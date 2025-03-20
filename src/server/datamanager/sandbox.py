"""
Copyright 2017-2024 SensiML Corporation

This file is part of SensiML™ Piccolo AI™.

SensiML Piccolo AI is free software: you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

SensiML Piccolo AI is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with SensiML Piccolo AI. If not, see <https://www.gnu.org/licenses/>.
"""

# pylint disable=redefined-builtin
import json
import logging
import sys
import traceback
from collections import deque
from io import BytesIO

import datamanager.pipeline_queue as pipeline_queue
from datamanager.models import (
    Project,
    Sandbox,
    TeamMember,
    Query,
    delete_caches_from_disk,
)
from datamanager.serializers import SandboxConfigSerializer, SandboxSerializer
from datamanager.serializers.utils import SandboxAsyncSerializer
from datamanager.tasks import (
    auto_async,
    autosegment_async,
    gridsearch_async,
    pipeline_async,
)
from datamanager.util_err_defs import FileErrors, GeneralErrors, SandboxErrors
from datamanager.utils.model_utils import _check_parents, _get_project, _locate_sandbox
from datamanager.utils.pipeline_codegen import generate_ipynb_code, generate_python_code
from django.conf import settings
from django.core import exceptions
from django.db.utils import IntegrityError
from django.http import FileResponse
from django.urls import re_path as url
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from engine.base import metrics
from engine.base.cache_manager import CacheManager
from engine.base.pipeline_utils import (
    make_pipeline_linear,
)
from engine.drivers import get_selected_features
from library.model_generators import model_generator
from logger.data_logger import usage_log
from logger.log_handler import LogHandler
from pandas import DataFrame, notnull, NA, concat
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import DjangoModelPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework.urlpatterns import format_suffix_patterns


logger = LogHandler(logging.getLogger(__name__))


class PipelineException(ValidationError):
    pass


def _init_device_config_with_budget(request):
    """Applies a default budget if the incoming config does not have a budget and matches a known known platform
    and version."""
    config = {}
    if "device_config" in request:
        config = request["device_config"]
        if not config.get("budget", False):
            config["budget"] = {}
    return config


def validate_pipeline(pipeline):
    for _, step in enumerate(pipeline):
        if step["name"] == "generator_set":
            if len(step["set"]) > settings.MAX_PIPELINE_FEATURES:
                raise PipelineException(
                    "To many features in pipeline. Max number of feature generators is {max_features}".format(
                        max_features=settings.MAX_PIPELINE_FEATURES
                    )
                )

        if step["name"] == "Windowing":
            if step["inputs"].get("train_delta", None):
                if (
                    step["inputs"].get("enable_train_delta", True)
                    and step["inputs"]["train_delta"]
                    < step["inputs"]["window_size"] * 0.25
                ):
                    raise PipelineException(
                        "The train_delta parameter in Windowing can not be less than 25% of the window_size."
                    )
            elif step["inputs"]["delta"] < step["inputs"]["window_size"] * 0.25:
                raise PipelineException(
                    "The delta parameter in the Windowing Segmenter can not be less than 25% of the window_size. If you want a smaller delta value for inference, set the train delta to a value >25%."
                )

    return pipeline


def get_label_column_from_pipeline(sandbox):
    label_column = None
    if len(sandbox.pipeline) > 0:
        query_step = next((x for x in sandbox.pipeline if x["type"] == "query"), None)
        if query_step is not None:
            query_object = Query.objects.get(
                name=query_step["name"], project=sandbox.project
            )
            label_column = query_object.label_column

    return label_column


def calculate_feature_stats(feature_data, feature_table, label_column, sandbox_uuid):
    (_ft, selected_features, selected_feature_cols) = get_selected_features(
        feature_table, sandbox_uuid
    )

    if len(selected_feature_cols) == 0:
        return {}

    if not isinstance(feature_data, DataFrame):
        return {}

    feature_statistics = {}
    if label_column and label_column in feature_data.columns:
        selected_feature_cols.append(label_column)
        feature_statistics = model_generator.compute_feature_stats(
            feature_data[selected_feature_cols]
        )

    feature_summary = (
        selected_features.where(notnull(selected_features), NA)
        .fillna("")
        .to_dict(orient="records")
    )

    return {
        "feature_statistics": model_generator.compute_feature_stats(
            feature_data[selected_feature_cols]
        ),
        "feature_summary": (
            selected_features.where(notnull(selected_features), NA)
            .fillna("")
            .to_dict(orient="records")
        ),
    }


class SandboxCrudMixin(object):
    """Adds CRUD operations to GenericAPIView derived classes"""

    def get_sandbox(self, request, project_uuid, many=False):
        serializer_class = self.get_serializer_class()
        if many is False:
            # Return the sandbox for a named event schema
            try:
                sandbox = self.get_object()
                data = serializer_class(sandbox, context={"request": request}).data
                # Fix for legacy JSON-in-JSON
                try:
                    if "pipeline" in data:
                        data["pipeline"] = json.loads(data["pipeline"])
                except (ValueError, TypeError):
                    pass
                return Response(data)
            except exceptions.ObjectDoesNotExist:
                raise NotFound()
        else:
            sandboxes = self.get_queryset()
            data = serializer_class(
                sandboxes, context={"request": request}, many=True
            ).data

            # Needed to fix badly saved pipeline data
            def fix_pipeline(sb):
                try:
                    if "popeline" in sb:
                        sb["pipeline"] = json.loads(sb["pipeline"])
                except (ValueError, TypeError):
                    pass
                return sb

            data = list(map(fix_pipeline, data))

            return Response(data)

    def post_sandbox(self, request, project_uuid):
        if _check_parents(request.user, project_uuid) and request.user.has_perm(
            "datamanager.add_sandbox"
        ):
            try:
                name = request.data["name"]
                try:
                    pipeline = request.data["pipeline"]
                except KeyError:
                    pipeline = request.data["steps"]
                cache_enabled = request.data.get("cache_enabled", True)
                hyper_params = request.data.get("hyper_params")
                device_config = _init_device_config_with_budget(request.data)

            except KeyError:
                logger.error(
                    {"message": traceback.format_exc(), "log_type": "datamanager"}
                )
                raise ValidationError(SandboxErrors.sandbox_invalid_format)

            project = _get_project(request.user, project_uuid)

            # validate sandbox is unique by the following constraint name_project_team
            if Sandbox.objects.filter(
                name=name,
                project__uuid=project_uuid,
                project__team=request.user.teammember.team,
            ):
                raise ValidationError("Pipeline names must be unique per project.")

            try:
                sandbox = Sandbox(
                    project=project,
                    name=name,
                    pipeline=validate_pipeline(make_pipeline_linear(pipeline)),
                    cache_enabled=cache_enabled,
                    device_config=device_config,
                    hyper_params=hyper_params,
                )

                sandbox.save()

                # Users are added to the pipeline by default
                sandbox.users.add(request.user)

                # To keep things consistent, enterprise users all team members
                if request.data.get("shared", True):
                    for user in TeamMember.objects.filter(
                        team=request.user.teammember.team
                    ):
                        sandbox.users.add(user)

                sandbox.save()
                return Response(
                    self.get_serializer_class()(
                        sandbox, context={"request": request}
                    ).data
                )
            except IntegrityError as e:
                logger.warning({"message": e, "log_type": "datamanager"})
                raise ValidationError(GeneralErrors.non_unique_id)
        else:
            raise NotFound(FileErrors.fil_inv_path)

    def put_sandbox(self, request, project_uuid):
        if _check_parents(request.user, project_uuid) and request.user.has_perm(
            "datamanager.change_sandbox"
        ):
            try:
                name = request.data["name"]
                try:
                    pipeline = request.data["pipeline"]
                except KeyError:
                    pipeline = request.data["steps"]

                cache_enabled = request.data.get("cache_enabled", True)
                device_config = _init_device_config_with_budget(request.data)
                hyper_params = request.data.get("hyper_params")

            except KeyError:
                logger.error(
                    {"message": traceback.format_exc(), "log_type": "datamanager"}
                )
                raise ValidationError(SandboxErrors.sandbox_invalid_format)
            try:
                sandbox = self.get_object()
                if sandbox.active:
                    return Response(
                        {
                            "detail": "Pipeline is currently running. Stop the pipeline or wait for it to finish before making changes."
                        },
                        status=400,
                    )

                sandbox.name = name
                sandbox.pipeline = validate_pipeline(make_pipeline_linear(pipeline))
                sandbox.cache_enabled = cache_enabled
                sandbox.device_config = device_config
                sandbox.hyper_params = hyper_params
                pipeline_queue.set_pipeline_task_id(project_uuid, sandbox.uuid)
                sandbox.save(
                    update_fields=[
                        "name",
                        "pipeline",
                        "cache_enabled",
                        "device_config",
                        "hyper_params",
                    ]
                )
                return Response(
                    self.get_serializer_class()(
                        sandbox, context={"request": request}
                    ).data
                )
            except exceptions.ObjectDoesNotExist as e:
                raise NotFound(SandboxErrors.sandbox_not_found)
        else:
            raise NotFound("invalid path to object")

    def delete_sandbox(self, request, project_uuid):
        if _check_parents(request.user, project_uuid) and request.user.has_perm(
            "datamanager.delete_sandbox"
        ):
            try:
                sandbox = self.get_object()
                if sandbox.active:
                    return Response(
                        {
                            "detail": "Pipeline is currently running. Stop the pipeline or wait for it to finish before making changes."
                        },
                        status=400,
                    )
                sandbox.name
                sandbox.delete()
                return Response(status=204)
            except exceptions.ObjectDoesNotExist as e:
                raise NotFound()
        else:
            raise NotFound(FileErrors.fil_inv_path)

    def __get_step_params(self):
        pass

    def sandbox_data(self, request, project_uuid):
        """Return the columns of data requested."""

        def str_to_bool(value):
            if not isinstance(value, str):
                return value

            return value.lower() == "true"

        sandbox = self.get_object()
        pipeline = sandbox.pipeline
        step = request.query_params.get("pipeline_step", None)
        if step is None:
            step = request.data.get("pipeline_step", None)
        page_index = request.query_params.get("page_index", None)
        if page_index is None:
            page_index = request.data.get("page_index", 0)

        sample_size = request.query_params.get("sample_size", None)
        if sample_size is None:
            sample_size = request.data.get("sample_size")

        convert_datasegments_to_dataframe = str_to_bool(
            request.query_params.get("convert_datasegments_to_dataframe", None)
        )
        if convert_datasegments_to_dataframe is None:
            convert_datasegments_to_dataframe = request.data.get(
                "convert_datasegments_to_dataframe", True
            )

        if not isinstance(convert_datasegments_to_dataframe, bool):
            raise Exception(
                "Invalid Parameter: convert_datasegments_to_dataframe must be bool"
            )

        if step:
            step = int(step)
        if page_index:
            page_index = int(page_index)
        if sample_size:
            sample_size = int(sample_size)

        if step is None:
            return Response(
                {"detail": "pipeline_step queryparam was not provided."},
                status=400,
            )

        # Perform some sanity checks to prevent collisions.
        if step not in range(len(pipeline)):
            return Response(
                {"detail": "Selected pipeline step is not in executed pipeline."},
                status=400,
            )

        if pipeline_queue.get_is_pipeline_active(project_uuid, sandbox.uuid):
            return Response({"detail": "Pipeline is currently running."}, status=400)

        cache_manager = CacheManager(sandbox, pipeline, pipeline_id=sandbox.uuid)

        data, number_of_pages = cache_manager.get_result_from_cache_with_sample_size(
            variable_name=pipeline[step]["outputs"][0],
            page_index=page_index,
            sample_size=sample_size,
            cache_key="data",
            convert_datasegments_to_dataframe=convert_datasegments_to_dataframe,
        )

        if data is None:
            return Response({"detail": "No data stored for this pipeline"}, status=400)

        project = Project.objects.get(uuid=project_uuid)

        usage_log(
            PJID=project,
            operation="pipeline_data",
            detail={"page_index": page_index, "data_size": sys.getsizeof(data)},
            team=project.team,
            team_member=request.user.teammember,
        )

        return Response(
            {
                "results": data,
                "extra": None,
                "summary": None,
                "number_of_pages": number_of_pages,
            }
        )

    def sandbox_features_stats(self, request, project_uuid):
        sandbox = self.get_object()
        pipeline = sandbox.pipeline

        step = request.query_params.get("pipeline_step", None)
        if step is None:
            step = request.data.get("pipeline_step", None)
        if step:
            step = int(step)

        sample_size = request.query_params.get("sample_size")
        if sample_size is None:
            sample_size = request.data.get("sample_size")
        if sample_size:
            sample_size = int(sample_size)

        if step is None:
            return Response(
                {"detail": "pipeline_step queryparam was not provided."},
                status=400,
            )
        if step not in range(len(pipeline)):
            return Response(
                {"detail": "Selected pipeline_step is not in executed pipeline."},
                status=400,
            )
        if len(pipeline[step]["outputs"]) < 2:
            return Response(
                {
                    "detail": f"No features data stored for pipeline step {pipeline[step]['name']}"
                },
                status=400,
            )
        if pipeline_queue.get_is_pipeline_active(project_uuid, sandbox.uuid):
            return Response({"detail": "Pipeline is currently running."}, status=400)

        cache_manager = CacheManager(sandbox, pipeline, pipeline_id=sandbox.uuid)

        data_name, features_name = pipeline[step]["outputs"]
        fd_index = ft_index = 0

        feature_data, data_pages = cache_manager.get_result_from_cache_with_sample_size(
            variable_name=data_name,
            page_index=fd_index,
            sample_size=sample_size,
            cache_key="data",
        )
        feature_table, ft_pages = cache_manager.get_result_from_cache_with_sample_size(
            variable_name=features_name,
            page_index=ft_index,
            sample_size=sample_size,
            cache_key="data",
        )

        if feature_data is None or feature_table is None:
            return Response(
                {"detail": "No features data stored for this pipeline"}, status=400
            )

        while fd_index < data_pages:
            fd_item, _ = cache_manager.get_result_from_cache_with_sample_size(
                variable_name=data_name,
                page_index=fd_index,
                sample_size=sample_size,
                cache_key="data",
            )
            sample_size
            concat([feature_data, fd_item])
            fd_index += 1

        while ft_index < ft_pages:
            ft_item, _ = cache_manager.get_result_from_cache_with_sample_size(
                variable_name=data_name,
                page_index=ft_index,
                sample_size=sample_size,
                cache_key="data",
            )
            concat([feature_table, ft_item])
            ft_index += 1

        project = Project.objects.get(uuid=project_uuid)
        label_column = get_label_column_from_pipeline(sandbox=sandbox) or "Label"

        usage_log(
            PJID=project,
            operation="pipeline_statistic",
            detail={"page_index": "1"},
            team=project.team,
            team_member=request.user.teammember,
        )

        return Response(
            {
                "label_column": label_column,
                "feature_data": feature_data,
                **calculate_feature_stats(
                    feature_data, feature_table, label_column, sandbox.uuid
                ),
            }
        )


class SandboxAsyncMixin(object):
    """Adds async operations to GenericAPIView derived classes"""

    def async_submit(self, request, project_uuid, sandbox_uuid, err_queue=deque()):
        """Put the sandbox execution task in a celery queue.
        Assembles a DataFrame from the sandbox pipeline and stores it in the sandbox cache.
        """

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        execution_type = request.data.get("execution_type", None)

        if execution_type not in [
            "pipeline",
            "grid_search",
            "auto",
            "automlv2",
            "autosegment_search",
        ]:
            raise ValidationError(
                "Invalid Execution Parameter for execution_type - {}".format(
                    execution_type
                )
            )

        sandbox = self.get_object()

        if sandbox.active:
            raise PipelineException(
                "Pipeline currently executing. Use stop_pipeline() to terminate."
            )

        pipeline_queue.set_start_sandbox(project_uuid, sandbox_uuid)

        sandbox.cpu_clock_time = 0
        sandbox.active = True
        sandbox.save(update_fields=["cpu_clock_time", "active"])

        if execution_type == "pipeline":
            message = "Pipeline submitted to queue"
            sent_job = pipeline_async.delay(request.user.id, project_uuid, sandbox_uuid)

        elif execution_type == "grid_search":
            message = "GridSearch Pipeline submitted to queue"
            grid_params = request.data.get("grid_params")
            run_parallel = request.data.get("run_parallel")
            sent_job = gridsearch_async.delay(
                request.user.id, project_uuid, sandbox_uuid, grid_params, run_parallel
            )

        elif execution_type in ["auto", "automlv2"]:
            message = "AutoML Pipeline submitted to queue"

            auto_params = request.data.get("auto_params")
            run_parallel = request.data.get("run_parallel")

            sent_job = auto_async.delay(
                request.user.id,
                project_uuid,
                sandbox_uuid,
                auto_params,
                run_parallel,
                execution_type,
            )

        elif execution_type == "autosegment_search":
            message = "Segment Optimization pipeline submitted to queue"

            seg_params = request.data.get("seg_params")
            run_parallel = request.data.get("run_parallel")
            sent_job = autosegment_async.delay(
                request.user.id, project_uuid, sandbox_uuid, seg_params, run_parallel
            )

        pipeline_queue.set_pipeline_task_id(
            project_uuid, sandbox_uuid, sent_job.task_id
        )

        logger.userlog(
            {
                "message": message,
                "log_type": "PID",
                "sandbox_uuid": sandbox_uuid,
                "project_uuid": project_uuid,
                "team_member_uuid": request.user.teammember.uuid,
                "task_id": sent_job.task_id,
            }
        )

        return Response(
            {
                "message": message,
                "log_type": "PID",
                "sandbox_uuid": sandbox_uuid,
                "project_uuid": project_uuid,
                "task_id": sent_job.task_id,
            },
            status=200,
        )

    def async_retrieve(self, request, project_uuid, sandbox_uuid, err_queue=deque()):
        """Return the asynchronous sandbox results requested.

        Assembles a DataFrame from the sandbox cache."""

        serializer = self.serializer_class(
            data=request.query_params, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        page_index = int(request.query_params.get("page_index", 0))
        status_report = request.query_params.get("status_only") == "True"

        sample_size = request.query_params.get("sample_size")
        if sample_size is None:
            sample_size = request.data.get("sample_size")

        if sample_size is not None:
            sample_size = int(sample_size)

        number_of_pages = 0

        sandbox = self.get_object()
        status, message, detail = pipeline_queue.get_pipeline_status(
            project_uuid, sandbox_uuid
        )

        # Data Studio expects a string or None
        if (
            hasattr(request.auth, "application")
            and request.auth.application.name == settings.OAUTH_DATA_STUDIO_CLIENT_NAME
        ):
            detail = None

        if status in ["PENDING", "STARTED", "REVOKED", "SENT"]:
            return Response(
                {
                    "status": status,
                    "message": message,
                    "detail": detail,
                    "errors": None,
                    "execution_type": sandbox.result_type,
                }
            )

        # Create a cache manager for retrieving results and errors
        cache_manager = CacheManager(
            sandbox, sandbox.pipeline, pipeline_id=sandbox_uuid
        )
        errors = cache_manager.get_cache_list("errors")
        statistics_summary = {}

        if status in ["FAILURE"]:
            return Response(
                {
                    "status": status,
                    "message": message,
                    "detail": detail,
                    "errors": errors,
                    "execution_type": sandbox.result_type,
                }
            )

        elif status_report and status in ["SUCCESS"]:
            return Response(
                {
                    "status": status,
                    "message": message,
                    "detail": detail,
                    "errors": None,
                    "execution_type": sandbox.result_type,
                }
            )

        elif status in [None]:
            return Response(
                {
                    "status": status,
                    "message": message,
                    "detail": detail,
                    "errors": None,
                    "execution_type": sandbox.result_type,
                }
            )

        elif status in ["SUCCESS"]:
            # Retrieve the sandbox's last cached result
            execution_summary = message
            summary = None

            try:
                if sandbox.result_type == "pipeline":
                    result_name = "pipeline_result.{}".format(sandbox_uuid)
                    feature_name = "feature_table.{}".format(sandbox_uuid)
                    (feature_table, _) = (
                        cache_manager.get_result_from_cache_with_sample_size(
                            variable_name=feature_name,
                            sample_size=sample_size,
                        )
                    )
                    (feature_data, _) = (
                        cache_manager.get_result_from_cache_with_sample_size(
                            variable_name=result_name,
                            sample_size=sample_size,
                        )
                    )
                    summary_key = "feature_table"
                    label_column = (
                        get_label_column_from_pipeline(sandbox=sandbox) or "Label"
                    )
                    statistics_summary = calculate_feature_stats(
                        feature_data, feature_table, label_column, sandbox.uuid
                    )
                    summary = feature_data

                elif sandbox.result_type == "grid_search":
                    result_name = "grid_result.{}".format(sandbox_uuid)
                    summary_key = "search_summary"

                elif sandbox.result_type == "auto":
                    result_name = "auto_models.{}".format(sandbox_uuid)
                    summary_name = "auto_extra.{}".format(sandbox_uuid)
                    (summary, _) = cache_manager.get_result_from_cache_with_sample_size(
                        variable_name=summary_name,
                        sample_size=sample_size,
                    )
                    summary_key = "fitness_summary"

                elif sandbox.result_type == "autosegment_search":
                    result_name = "autosegmentation_result.{}".format(sandbox_uuid)
                    summary_name = "auto_segment_summary.{}".format(sandbox_uuid)
                    (summary, _) = cache_manager.get_result_from_cache_with_sample_size(
                        variable_name=summary_name,
                        sample_size=sample_size,
                    )
                    summary_key = "segment_summary"

                else:
                    raise FileNotFoundError(
                        f"Sandbox result type '{sandbox.result_type}' not supported."
                    )

            except FileNotFoundError as e:
                return Response(
                    {
                        "status": None if status is None else "FAILURE",
                        "message": "No results stored for this pipeline.",
                        "detail": {"error": str(e)},
                    }
                )

            (data, number_of_pages) = (
                cache_manager.get_result_from_cache_with_sample_size(
                    variable_name=result_name,
                    sample_size=sample_size,
                    page_index=page_index,
                )
            )

            if data is None:
                return Response(
                    {
                        "status": None if status is None else "FAILURE",
                        "message": "No results stored for this pipeline.",
                        "detail": None,
                    }
                )

            if summary is None:
                summary = []

            if isinstance(summary, DataFrame):
                summary.fillna(value="", inplace=True)

            def sanitize_return(value):
                if isinstance(value, DataFrame):
                    return value

                if not value:
                    return None

                return value

            return Response(
                {
                    "results": sanitize_return(data),
                    "status": "SUCCESS",
                    summary_key: sanitize_return(summary),
                    "statistics_summary": sanitize_return(statistics_summary),
                    "execution_summary": sanitize_return(execution_summary),
                    "page_index": page_index,
                    "number_of_pages": number_of_pages,
                    "errors": sanitize_return(errors),
                    "execution_type": sandbox.result_type,
                }
            )

    def kill_pipeline(self, request, project_uuid, sandbox_uuid):
        # delete the status from the queue
        result = pipeline_queue.kill_sandbox(project_uuid, sandbox_uuid)

        if result.task_id:
            logger.userlog(
                {
                    "message": "pipeline execution terminated",
                    "log_type": "PID",
                    "sandbox_uuid": sandbox_uuid,
                    "project_uuid": project_uuid,
                    "task_id": result.task_id,
                }
            )

            return Response(
                "Pipeline '{}' execution was terminated.".format(result.task_id)
            )
        else:
            return Response("Pipeline is not currently running.")


@extend_schema_view(
    post=extend_schema(
        summary="Generate metrics for y_true and y_pred",
        description="""Builds a metric result dictionary of f1_score, precision, sensitivity, specificity, accuracy,
        positive_predictive_rate, ConfusionMatrix given a list of y_true and y_pred""",
        parameters=[OpenApiParameter(name="y_true"), OpenApiParameter(name="y_pred")],
    ),
    tags=["Reporting"],
)
@api_view(("POST",))
@permission_classes((IsAuthenticated,))
def sandbox_get_metrics_set(request, err_queue=deque()):
    metrics_set = metrics.get_metrics_set(request.data)
    return Response({"results": metrics_set})


@extend_schema_view(
    delete=extend_schema(
        summary="Delete the cache for a sandbox",
        description="Delete the cached data inside a sandbox created during a pipeline execution",
    ),
)
@api_view(("DELETE",))
@permission_classes((IsAuthenticated,))
def delete_sandbox_cache(request, project_uuid, sandbox_uuid, err_queue=deque()):
    sandbox = _locate_sandbox(request.user, project_uuid, sandbox_uuid)
    if sandbox.cache:
        try:
            cache = sandbox.cache
        except TypeError:
            cache = sandbox.cache
        if "pipeline" in cache and len(cache["pipeline"]):
            # Delete everything in the cache
            delete_caches_from_disk(sender=Sandbox, instance=sandbox)
            sandbox.cache = None
            sandbox.save(update_fields=["cache"])
            return Response(status=204)

    return Response('Sandbox "{0}" cache is already empty'.format(sandbox.name))


@extend_schema_view(
    get=extend_schema(
        summary="Get A Python File",
        description="Get the python SDK version of the current pipeline",
    ),
)
@api_view(("GET",))
@permission_classes((IsAuthenticated,))
def pipeline_to_python(request, project_uuid, sandbox_uuid):
    sandbox = _locate_sandbox(request.user, project_uuid, sandbox_uuid)

    python_template = generate_python_code(sandbox)

    file_buffer = BytesIO()
    file_buffer.write(python_template.encode())
    file_buffer.seek(0)

    response = FileResponse(file_buffer)
    # Set the content type for the response
    response["Content-Type"] = "application/octet-stream"
    # Optionally, specify the file name for the downloaded file
    response["Content-Disposition"] = f'attachment; filename="{sandbox.name}.py"'
    return response


@extend_schema_view(
    get=extend_schema(
        summary="Get A Python File",
        description="Get the python SDK version of the current pipeline",
    ),
)
@api_view(("GET",))
@permission_classes((IsAuthenticated,))
def pipeline_to_ipynb(request, project_uuid, sandbox_uuid):
    sandbox = _locate_sandbox(request.user, project_uuid, sandbox_uuid)

    python_template = generate_ipynb_code(sandbox)

    file_buffer = BytesIO()
    file_buffer.write(python_template.encode())
    file_buffer.seek(0)

    response = FileResponse(file_buffer)
    # Set the content type for the response
    response["Content-Type"] = "application/octet-stream"
    # Optionally, specify the file name for the downloaded file
    response["Content-Disposition"] = f'attachment; filename="{sandbox.name}.ipynb"'
    return response


# filter query statistic sandbox
def filter_query_statistic_sandbox(request_user, project_uuid):
    return Sandbox.objects.filter(
        project__uuid=project_uuid,
        project__team=request_user.teammember.team,
        private=False,
    )


@extend_schema_view(
    get=extend_schema(
        summary="List all sandboxes for a project by UUID",
        description="Returns all sandboxes that are associated with a specific project",
        parameters=[
            OpenApiParameter(
                name="fields[]",
                description="Optional to include fields to response.",
                examples=[OpenApiExample(name="?fields[]=uuid&fields[]=name")],
            ),
            OpenApiParameter(
                name="omit_fields[]",
                description="Optional to exclude fields from response.",
                examples=[
                    OpenApiExample(name="?omit_fields[]=uuid&omit_fields[]=name")
                ],
            ),
        ],
    ),
    post=extend_schema(
        summary="Create a new sandbox inside a project",
        description="Creates a new sandbox",
    ),
)
class SandboxListCreateView(SandboxCrudMixin, generics.GenericAPIView):
    permissions = (IsAuthenticated, DjangoModelPermissions)
    serializer_class = SandboxSerializer

    def get_queryset(self):
        return filter_query_statistic_sandbox(
            self.request.user, self.kwargs["project_uuid"]
        )

    def get(self, request, *args, **kwargs):
        return self.get_sandbox(request, self.kwargs["project_uuid"], many=True)

    def post(self, request, *args, **kwargs):
        return self.post_sandbox(request, self.kwargs["project_uuid"])


@extend_schema_view(
    get=extend_schema(
        summary="Get detailed sandbox information by UUID",
        description="Returns information about a single sandbox that are associated with a specific project",
        parameters=[
            OpenApiParameter(
                name="fields[]",
                description="Optional to include fields to response.",
                examples=[OpenApiExample(name="?fields[]=uuid&fields[]=name")],
            ),
            OpenApiParameter(
                name="omit_fields[]",
                description="Optional to exclude fields from response.",
                examples=[
                    OpenApiExample(name="?omit_fields[]=uuid&omit_fields[]=name")
                ],
            ),
        ],
    ),
    put=extend_schema(
        summary="Update the sandbox properties",
        description="Update information about the sandbox such as the pipeline json, name and hyperparameters",
    ),
    patch=extend_schema(
        summary="Update the sandbox properties",
        description="Update information about the sandbox such as the pipeline json, name and hyperparameters",
    ),
    delete=extend_schema(
        summary="Delete a sandbox",
        description="Delete a sandbox all its associated knowledge packs and cached data",
    ),
)
class SandboxDetailView(SandboxCrudMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated, DjangoModelPermissions)
    serializer_class = SandboxSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return filter_query_statistic_sandbox(
            self.request.user, self.kwargs["project_uuid"]
        )

    def get(self, request, *args, **kwargs):
        return self.get_sandbox(request, self.kwargs["project_uuid"], many=False)

    def put(self, request, *args, **kwargs):
        return self.put_sandbox(request, self.kwargs["project_uuid"])

    def patch(self, request, *args, **kwargs):
        return self.put_sandbox(request, self.kwargs["project_uuid"])

    def delete(self, request, *args, **kwargs):
        if request.user.has_perm("datamanager.delete_sandbox"):
            return self.delete_sandbox(request, self.kwargs["project_uuid"])
        else:
            raise PermissionDenied()


@extend_schema_view(
    get=extend_schema(
        summary="Get information about the sandbox configuration by UUID",
        description="Returns information about a single sandbox configuration",
    ),
)
class SandboxConfigListView(generics.RetrieveAPIView):
    serializer_class = SandboxConfigSerializer
    queryset = Sandbox.objects.none()
    permission_classes = (permissions.DjangoModelPermissions,)
    lookup_field = "uuid"

    def get_queryset(self):
        return Sandbox.objects.with_user(self.request.user).filter(
            project__uuid=self.kwargs["project_uuid"]
        )


@extend_schema_view(
    get=extend_schema(
        summary="Get the data from an executed pipeline inside the sandbox",
        description="Returns the output of a pipeline corresponding to the requested page index",
    ),
)
class SandboxDataView(SandboxCrudMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated, DjangoModelPermissions)
    lookup_field = "uuid"

    def get_queryset(self):
        return filter_query_statistic_sandbox(
            self.request.user, self.kwargs["project_uuid"]
        )

    def get(self, request, *args, **kwargs):
        return self.sandbox_data(request, self.kwargs["project_uuid"])


class SandboxFeatureStatsView(SandboxCrudMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated, DjangoModelPermissions)
    lookup_field = "uuid"

    def get_queryset(self):
        return filter_query_statistic_sandbox(
            self.request.user, self.kwargs["project_uuid"]
        )

    def get(self, request, *args, **kwargs):
        return self.sandbox_features_stats(request, self.kwargs["project_uuid"])


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve sandbox status or results if completed",
        description="""
        Retrieve sandbox status or results if completed
            * Optional querystring field: `execution_type` should be either `pipeline` or `grid_search`
            * Optional querystring field: `page_index` should be the page desired if the result is multi-page
        """,
    ),
    post=extend_schema(
        summary="Submit a request to execute the pipeline stored in the sandbox",
        description="The sandbox will execute the pipeline asynchronously on the server",
    ),
    delete=extend_schema(
        summary="Stop currently executing pipeline",
        description="Stop currently executing pipeline",
    ),
)
class SandboxAsyncView(SandboxAsyncMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated, DjangoModelPermissions)
    serializer_class = SandboxAsyncSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return Sandbox.objects.with_user(self.request.user).all()

    def get(self, request, *args, **kwargs):
        return self.async_retrieve(
            request, self.kwargs["project_uuid"], self.kwargs["uuid"]
        )

    def post(self, request, *args, **kwargs):
        return self.async_submit(
            request, self.kwargs["project_uuid"], self.kwargs["uuid"]
        )

    def delete(self, request, *args, **kwargs):
        return self.kill_pipeline(
            request, self.kwargs["project_uuid"], self.kwargs["uuid"]
        )


urlpatterns = format_suffix_patterns(
    [
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/$",
            SandboxListCreateView.as_view(),
            name="sandbox-list",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<uuid>[^/]+)/$",
            SandboxDetailView.as_view(),
            name="sandbox-detail",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<uuid>[^/]+)/data/$",
            SandboxDataView.as_view(),
            name="sandbox-data",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<uuid>[^/]+)/features-stats/",
            SandboxFeatureStatsView.as_view(),
            name="sandbox-features-statistic",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox-async/(?P<uuid>[^/]+)/$",
            SandboxAsyncView.as_view(),
            name="sandbox-async",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<sandbox_uuid>[^/]+)/cache/$",
            delete_sandbox_cache,
            name="sandbox-cache-delete",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<uuid>[^/]+)/device_config/$",
            SandboxConfigListView.as_view(),
            name="sandbox-config",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<sandbox_uuid>[^/]+)/python/$",
            pipeline_to_python,
            name="sandbox-to-python",
        ),
        url(
            r"^project/(?P<project_uuid>[^/]+)/sandbox/(?P<sandbox_uuid>[^/]+)/ipynb/$",
            pipeline_to_ipynb,
            name="sandbox-to-ipynb",
        ),
    ]
)
