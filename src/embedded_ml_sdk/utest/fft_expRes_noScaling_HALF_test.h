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

// Expected Results for fft_noScaling_HALF_test
#
static const float fft_expRes_noScaling_HALF_test[512] = \
{
    101.0, 101.0,
    -11.0, -198.0,
    -139.0, -3.0,
    -1.0, 70.0,
    30.0, -6.0,
    -6.0, -22.0,
    -13.0, 3.0,
    4.0, -4.0,
    -10.0, -10.0,
    -4.0, 10.0,
    5.0, -9.0,
    -10.0, -3.0,
    1.0, -1.0,
    -4.0, -8.0,
    -3.0, 3.0,
    3.0, -4.0,
    -2.0, -1.0,
    1.0, -1.0,
    -3.0, -3.0,
    -1.0, -1.0,
    -1.0, -5.0,
    -6.0, -2.0,
    1.0, -1.0,
    -4.0, -4.0,
    -1.0, -1.0,
    0.0, -2.0,
    -1.0, -1.0,
    -1.0, -1.0,
    -1.0, -1.0,
    0.0, -1.0,
    -2.0, -2.0,
    -1.0, -1.0,
    1.0, -2.0,
    0.0, -1.0,
    -1.0, -1.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, -1.0,
    -1.0, 0.0,
    0.0, 0.0,
    -2.0, -2.0,
    -1.0, 0.0,
    -1.0, -3.0,
    -2.0, -1.0,
    -1.0, -1.0,
    0.0, -1.0,
    -1.0, 0.0,
    0.0, -1.0,
    -2.0, -1.0,
    0.0, -1.0,
    -1.0, -1.0,
    0.0, -1.0,
    0.0, -1.0,
    -1.0, -1.0,
    0.0, -1.0,
    0.0, -1.0,
    -1.0, -1.0,
    -1.0, -1.0,
    -2.0, -1.0,
    -1.0, -1.0,
    -2.0, -3.0,
    -2.0, -3.0,
    0.0, -1.0,
    -1.0, -1.0,
    0.0, -2.0,
    0.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    1.0, -2.0,
    -1.0, -3.0,
    0.0, 0.0,
    0.0, 0.0,
    -2.0, -1.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    1.0, -2.0,
    0.0, 0.0,
    1.0, -2.0,
    -2.0, 0.0,
    0.0, 0.0,
    0.0, -1.0,
    1.0, -2.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    -2.0, -2.0,
    -1.0, 0.0,
    0.0, 0.0,
    0.0, -1.0,
    1.0, -2.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, -2.0,
    0.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    1.0, -2.0,
    0.0, 0.0,
    -2.0, -1.0,
    0.0, 0.0,
    0.0, -1.0,
    0.0, -2.0,
    -1.0, 0.0,
    0.0, -2.0,
    0.0, -2.0,
    0.0, -1.0,
    0.0, -2.0,
    -1.0, 0.0,
    0.0, -1.0,
    -2.0, -1.0,
    0.0, -1.0,
    0.0, -1.0,
    -1.0, -1.0,
    0.0, -1.0,
    -1.0, -1.0,
    0.0, -2.0,
    -2.0, -3.0,
    -2.0, -2.0,
    -2.0, -3.0,
    -1.0, -1.0,
    -1.0, -2.0,
    1.0, -2.0,
    0.0, -2.0,
    0.0, -1.0,
    0.0, 0.0,
    1.0, 1.0,
    0.0, 0.0,
    0.0, 1.0,
    0.0, 2.0,
    -1.0, 0.0,
    -1.0, 2.0,
    -1.0, 1.0,
    0.0, 1.0,
    0.0, 0.0,
    0.0, 1.0,
    0.0, 2.0,
    -1.0, 1.0,
    0.0, 1.0,
    -1.0, 1.0,
    0.0, 1.0,
    0.0, 1.0,
    -2.0, 1.0,
    0.0, 1.0,
    -1.0, 0.0,
    0.0, 2.0,
    0.0, 1.0,
    0.0, 2.0,
    0.0, 2.0,
    -1.0, 0.0,
    0.0, 2.0,
    0.0, 1.0,
    0.0, 0.0,
    0.0, -1.0,
    0.0, 0.0,
    -1.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 2.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 1.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 1.0,
    0.0, 0.0,
    -2.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, -1.0,
    0.0, 0.0,
    0.0, 0.0,
    -1.0, -1.0,
    -1.0, 0.0,
    -1.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    0.0, 2.0,
    -1.0, 1.0,
    0.0, 1.0,
    0.0, 1.0,
    0.0, 1.0,
    -1.0, 1.0,
    0.0, 3.0,
    -1.0, 1.0,
    -1.0, 1.0,
    0.0, 1.0,
    0.0, 1.0,
    -1.0, 1.0,
    0.0, 1.0,
    0.0, 1.0,
    -1.0, 1.0,
    0.0, 1.0,
    -2.0, 1.0,
    0.0, 1.0,
    -1.0, 0.0,
    0.0, 1.0,
    -1.0, 1.0,
    -2.0, 1.0,
    -1.0, -1.0,
    -1.0, 0.0,
    0.0, 0.0,
    0.0, 0.0,
    -1.0, 0.0,
    0.0, 1.0,
    -1.0, 0.0,
    0.0, 0.0,
    -1.0, 1.0,
    0.0, 1.0,
    -1.0, 0.0,
    -1.0, 1.0,
    0.0, 0.0,
    0.0, 1.0,
    -1.0, 1.0,
    -1.0, 1.0,
    -1.0, 1.0,
    -2.0, 0.0,
    -1.0, 1.0,
    -2.0, 2.0,
    -1.0, 1.0,
    -2.0, 4.0,
    -1.0, 1.0,
    -1.0, 1.0,
    1.0, 1.0,
    -1.0, 1.0,
    -2.0, 1.0,
    -3.0, 2.0,
    -3.0, 1.0,
    -2.0, 2.0,
    -1.0, 1.0,
    -2.0, 3.0,
    -1.0, 3.0,
    -2.0, 2.0,
    -2.0, 2.0,
    -2.0, 2.0,
    -3.0, 3.0,
    -2.0, 6.0,
    0.0, 4.0,
    -3.0, 4.0,
    -1.0, 5.0,
    -1.0, 6.0,
};
