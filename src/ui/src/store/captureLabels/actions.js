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

import api, { throwParsedApiError } from "store/api";
import logger from "store/logger";
import helper from "store/helper";

import { LOAD_CAPTURES_LABELS, STORE_CAPTURES_LABELS } from "./actionTypes";

export const loadCaptureLabels = (projectUUID, captureUUID) => async (dispatch) => {
  let labels = [];
  try {
    dispatch({ type: LOAD_CAPTURES_LABELS });
    const { data } = await api.get(
      `/project/${projectUUID}/capture/${captureUUID}/label-relationship/`,
    );
    labels = data;
    dispatch({ type: STORE_CAPTURES_LABELS, payload: data });
  } catch (error) {
    logger.logError(
      "",
      `${helper.getResponseErrorDetails(error)} \n--project:${projectUUID}`,
      error,
      "loadCapturesLabel",
    );
    throwParsedApiError(error, "capture labels loading");
  }
  return labels;
};

export const clearCaptureLabels = () => async (dispatch) => {
  dispatch({ type: STORE_CAPTURES_LABELS, payload: [] });
};

export const createCaptureLabels =
  (projectUUID, sessionID, captureLabelList) => async (dispatch) => {
    try {
      const { data } = await api.post(
        `/v2/project/${projectUUID}/segmenter/${sessionID}/label-relationship/`,
        captureLabelList,
      );
      dispatch({ type: STORE_CAPTURES_LABELS, payload: data });
    } catch (error) {
      logger.logError(
        "",
        `${helper.getResponseErrorDetails(error)} \n--project:${projectUUID}`,
        error,
        "loadCapturesLabel",
      );
      throwParsedApiError(error, "capture labels updating");
    }
  };

export const updateCaptureLabels =
  (projectUUID, sessionID, captureLabelList) => async (dispatch) => {
    try {
      const { data } = await api.put(
        `/v2/project/${projectUUID}/segmenter/${sessionID}/label-relationship/`,
        captureLabelList,
      );
      dispatch({ type: STORE_CAPTURES_LABELS, payload: data });
    } catch (error) {
      logger.logError(
        "",
        `${helper.getResponseErrorDetails(error)} \n--project:${projectUUID}`,
        error,
        "loadCapturesLabel",
      );
      throwParsedApiError(error, "capture labels updating");
    }
  };

export const deleteCaptureLabels =
  (projectUUID, sessionID, captureLabelList) => async (dispatch) => {
    try {
      const { data } = await api.post(
        `/v2/project/${projectUUID}/label-relationship/delete/`,
        captureLabelList,
      );
      dispatch({ type: STORE_CAPTURES_LABELS, payload: data });
    } catch (error) {
      logger.logError(
        "",
        `${helper.getResponseErrorDetails(error)} \n--project:${projectUUID}`,
        error,
        "loadCapturesLabel",
      );
      throwParsedApiError(error, "capture labels deleting");
    }
  };
