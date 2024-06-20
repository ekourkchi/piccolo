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




#include "kbalgorithms.h"

int32_t fg_shape_ratio_high_frequency(kb_model_t *kb_model, int16_data_t *cols_to_use, float_data_t *params, FLOAT *pFV)
{
#define FG_SHAPE_RATIO_HIGH_FREQUENCY_NUM_PARAMS 1
#define FG_SHAPE_RATIO_HIGH_FREQUENCY_SMOOTHING_FACTOR_PARAM_IDX 0
	int32_t icol;
	FLOAT secondhalf, firsthalf;
	int32_t sf = (int32_t)params->data[FG_SHAPE_RATIO_HIGH_FREQUENCY_SMOOTHING_FACTOR_PARAM_IDX];

	for (icol = 0; icol < cols_to_use->size; icol++)
	{
		ratio_diff_impl(kb_model->pdata_buffer->data + cols_to_use->data[icol], kb_model->sg_index, kb_model->sg_length / 2, sf, 1, &secondhalf);
		ratio_diff_impl(kb_model->pdata_buffer->data + cols_to_use->data[icol], kb_model->sg_index, kb_model->sg_length / 2, sf, 0, &firsthalf);

		if (firsthalf < .001)
		{
			pFV[icol] = 0;
		}
		else
		{
			pFV[icol] = secondhalf / firsthalf;
		}
	}
	return cols_to_use->size;
}
