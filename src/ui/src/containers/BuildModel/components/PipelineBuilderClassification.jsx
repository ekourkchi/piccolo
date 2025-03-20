/*
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
*/

import React, { useMemo, useCallback } from "react";
import _ from "lodash";
import {
  AUTOML_SEARCHED_STEPS_TYPES_LOOKUP,
  PIPELINE_STEP_TYPES,
  PIPELINE_GROUPS,
} from "store/autoML/const";

import PipelineBuilderV1 from "components/PipelineBuilderV1";

const PipelineBuilderAutoML = ({ isAutoML, pipelineSettings, ...props }) => {
  const { selectedSteps, pipelineData } = props;

  const getCoveredSearchedStep = useCallback(() => {
    // AUTOML SEARCHED STEPS

    if (!isAutoML) {
      return [];
    }

    // find all steps from inputData AutoML form
    return AUTOML_SEARCHED_STEPS_TYPES_LOOKUP.reduce(
      (acc, el) => {
        if (pipelineSettings?.data[el.paramName]) {
          acc.push(el.stepType);
        }
        return acc;
      },
      [PIPELINE_STEP_TYPES.AUTOML_PARAMS],
    );
  }, [pipelineSettings, isAutoML]);

  const getFilteredSelectedSteps = useMemo(() => {
    const getOptimizedByAutoML = (type) => {
      return getCoveredSearchedStep().includes(type);
    };

    const isStepCached = (pipelineStep, pipelineStepCache) => {
      if (!pipelineStep || !pipelineStepCache) {
        return false;
      }
      if (pipelineStepCache?.name !== pipelineStep.name) {
        return false;
      }
      if (!_.isEmpty(pipelineStep?.set)) {
        return _.isEqual(pipelineStep?.set, pipelineStepCache?.set);
      }

      return _.isEqual(pipelineStep?.inputs, pipelineStepCache?.inputs);
    };

    const getStepType = (isAfterFeatureGenerator, isTVO) => {
      if (isTVO) {
        return PIPELINE_GROUPS.TVO.type;
      }
      if (isAfterFeatureGenerator) {
        return PIPELINE_GROUPS.FEATURE_EXTRACTOR.type;
      }
      return PIPELINE_GROUPS.PREPROCESSING.type;
    };

    if (!_.isEmpty(selectedSteps) && !_.isEmpty(pipelineData)) {
      let isStepCacheChanged = false;
      let isAfterFeatureGenerator = false;
      let isTVO = false;

      const res = selectedSteps
        .filter((step) => !step?.options?.isSessionSegmenter)
        .map((step, index) => {
          const pipelineStep = pipelineData?.pipeline ? pipelineData?.pipeline[index] : {};
          const pipelineStepCache = pipelineData?.cache?.pipeline[index];

          const getOutputCacheData = () => {
            const cachedItemsObj = {};
            const outputName = pipelineStep?.outputs[0];
            let isHasDistributionData = false;

            if (outputName) {
              const cacheItems = _.isArray(pipelineData?.cache?.data[outputName])
                ? pipelineData?.cache?.data[outputName]
                : [pipelineData?.cache?.data[outputName]];

              cacheItems.forEach((obj, indexPage) => {
                if (
                  !_.isEmpty(obj.distribution_segments) ||
                  !_.isEmpty(obj.distribution_feature_vectors) ||
                  !_.isEmpty(obj.distribution_samples)
                ) {
                  isHasDistributionData = true;
                }
                cachedItemsObj[obj.filename] = {
                  indexStep: index,
                  indexPage,
                  stepName: step.name,
                  distributionSegments: obj.distribution_segments,
                  distributionFeatureVectors: obj.distribution_feature_vectors,
                  distributionSamples: obj.distribution_samples,
                };
              });
            }
            return [cachedItemsObj, isHasDistributionData];
          };
          // feature_columns
          let isCached = false;
          if (isStepCached(pipelineStep, pipelineStepCache)) {
            isCached = true;
          } else {
            isStepCacheChanged = true;
          }
          if (step.type === PIPELINE_STEP_TYPES.FEATURE_GENERATOR) {
            isAfterFeatureGenerator = true;
          }
          if (step.type === PIPELINE_STEP_TYPES.CLASSIFIER) {
            isTVO = true;
          }
          let cacheData = {};
          let isHasDistributionData = false;

          if (isCached && !isStepCacheChanged) {
            [cacheData, isHasDistributionData] = getOutputCacheData();
          }
          return {
            ...step,
            index,
            options: {
              isCached: isCached && !isStepCacheChanged, // all next cache steps are ignored
              cacheData,
              isHasDistributionData,
              type: getStepType(isAfterFeatureGenerator, isTVO),
              isAfterFeatureGenerator,
              ...step.options,
              isOptimizedByAutoML: getOptimizedByAutoML(step.type),
            },
          };
        });

      return res;
    }
    return [];
  }, [selectedSteps, pipelineData]);

  return (
    <>
      <PipelineBuilderV1
        {...props}
        isAutoML={isAutoML}
        pipelineSettings={pipelineSettings}
        isModel={true}
        selectedSteps={getFilteredSelectedSteps}
      />
    </>
  );
};

export default PipelineBuilderAutoML;
