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




#include "fixlog.h"

#include <stdint.h>

/* Internal log-addition table for natural log with radix point at 8
 * bits.  Each entry is 256 * log(1 + e^{-n/256}).  This is used in the
 * log-add computation:
 *
 * e^z = e^x + e^y
 * e^z = e^x(1 + e^{y-x})     = e^y(1 + e^{x-y})
 * z   = x + log(1 + e^{y-x}) = y + log(1 + e^{x-y})
 *
 * So when y > x, z = y + logadd_table[-(x-y)]
 *    when x > y, z = x + logadd_table[-(y-x)]
 */
static const uint8_t fe_logadd_table[] = {
    177, 177, 176, 176, 175, 175, 174, 174, 173, 173,
    172, 172, 172, 171, 171, 170, 170, 169, 169, 168,
    168, 167, 167, 166, 166, 165, 165, 164, 164, 163,
    163, 162, 162, 161, 161, 161, 160, 160, 159, 159,
    158, 158, 157, 157, 156, 156, 155, 155, 155, 154,
    154, 153, 153, 152, 152, 151, 151, 151, 150, 150,
    149, 149, 148, 148, 147, 147, 147, 146, 146, 145,
    145, 144, 144, 144, 143, 143, 142, 142, 141, 141,
    141, 140, 140, 139, 139, 138, 138, 138, 137, 137,
    136, 136, 136, 135, 135, 134, 134, 134, 133, 133,
    132, 132, 131, 131, 131, 130, 130, 129, 129, 129,
    128, 128, 128, 127, 127, 126, 126, 126, 125, 125,
    124, 124, 124, 123, 123, 123, 122, 122, 121, 121,
    121, 120, 120, 119, 119, 119, 118, 118, 118, 117,
    117, 117, 116, 116, 115, 115, 115, 114, 114, 114,
    113, 113, 113, 112, 112, 112, 111, 111, 110, 110,
    110, 109, 109, 109, 108, 108, 108, 107, 107, 107,
    106, 106, 106, 105, 105, 105, 104, 104, 104, 103,
    103, 103, 102, 102, 102, 101, 101, 101, 100, 100,
    100, 99, 99, 99, 98, 98, 98, 97, 97, 97,
    96, 96, 96, 96, 95, 95, 95, 94, 94, 94,
    93, 93, 93, 92, 92, 92, 92, 91, 91, 91,
    90, 90, 90, 89, 89, 89, 89, 88, 88, 88,
    87, 87, 87, 87, 86, 86, 86, 85, 85, 85,
    85, 84, 84, 84, 83, 83, 83, 83, 82, 82,
    82, 82, 81, 81, 81, 80, 80, 80, 80, 79,
    79, 79, 79, 78, 78, 78, 78, 77, 77, 77,
    77, 76, 76, 76, 75, 75, 75, 75, 74, 74,
    74, 74, 73, 73, 73, 73, 72, 72, 72, 72,
    71, 71, 71, 71, 71, 70, 70, 70, 70, 69,
    69, 69, 69, 68, 68, 68, 68, 67, 67, 67,
    67, 67, 66, 66, 66, 66, 65, 65, 65, 65,
    64, 64, 64, 64, 64, 63, 63, 63, 63, 63,
    62, 62, 62, 62, 61, 61, 61, 61, 61, 60,
    60, 60, 60, 60, 59, 59, 59, 59, 59, 58,
    58, 58, 58, 58, 57, 57, 57, 57, 57, 56,
    56, 56, 56, 56, 55, 55, 55, 55, 55, 54,
    54, 54, 54, 54, 53, 53, 53, 53, 53, 52,
    52, 52, 52, 52, 52, 51, 51, 51, 51, 51,
    50, 50, 50, 50, 50, 50, 49, 49, 49, 49,
    49, 49, 48, 48, 48, 48, 48, 48, 47, 47,
    47, 47, 47, 47, 46, 46, 46, 46, 46, 46,
    45, 45, 45, 45, 45, 45, 44, 44, 44, 44,
    44, 44, 43, 43, 43, 43, 43, 43, 43, 42,
    42, 42, 42, 42, 42, 41, 41, 41, 41, 41,
    41, 41, 40, 40, 40, 40, 40, 40, 40, 39,
    39, 39, 39, 39, 39, 39, 38, 38, 38, 38,
    38, 38, 38, 37, 37, 37, 37, 37, 37, 37,
    37, 36, 36, 36, 36, 36, 36, 36, 35, 35,
    35, 35, 35, 35, 35, 35, 34, 34, 34, 34,
    34, 34, 34, 34, 33, 33, 33, 33, 33, 33,
    33, 33, 32, 32, 32, 32, 32, 32, 32, 32,
    32, 31, 31, 31, 31, 31, 31, 31, 31, 31,
    30, 30, 30, 30, 30, 30, 30, 30, 30, 29,
    29, 29, 29, 29, 29, 29, 29, 29, 28, 28,
    28, 28, 28, 28, 28, 28, 28, 28, 27, 27,
    27, 27, 27, 27, 27, 27, 27, 27, 26, 26,
    26, 26, 26, 26, 26, 26, 26, 26, 25, 25,
    25, 25, 25, 25, 25, 25, 25, 25, 25, 24,
    24, 24, 24, 24, 24, 24, 24, 24, 24, 24,
    23, 23, 23, 23, 23, 23, 23, 23, 23, 23,
    23, 23, 22, 22, 22, 22, 22, 22, 22, 22,
    22, 22, 22, 22, 21, 21, 21, 21, 21, 21,
    21, 21, 21, 21, 21, 21, 21, 20, 20, 20,
    20, 20, 20, 20, 20, 20, 20, 20, 20, 20,
    19, 19, 19, 19, 19, 19, 19, 19, 19, 19,
    19, 19, 19, 19, 18, 18, 18, 18, 18, 18,
    18, 18, 18, 18, 18, 18, 18, 18, 18, 17,
    17, 17, 17, 17, 17, 17, 17, 17, 17, 17,
    17, 17, 17, 17, 16, 16, 16, 16, 16, 16,
    16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
    16, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 14, 14,
    14, 14, 14, 14, 14, 14, 14, 14, 14, 14,
    14, 14, 14, 14, 14, 14, 14, 13, 13, 13,
    13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
    13, 13, 13, 13, 13, 13, 13, 12, 12, 12,
    12, 12, 12, 12, 12, 12, 12, 12, 12, 12,
    12, 12, 12, 12, 12, 12, 12, 12, 12, 11,
    11, 11, 11, 11, 11, 11, 11, 11, 11, 11,
    11, 11, 11, 11, 11, 11, 11, 11, 11, 11,
    11, 11, 11, 10, 10, 10, 10, 10, 10, 10,
    10, 10, 10, 10, 10, 10, 10, 10, 10, 10,
    10, 10, 10, 10, 10, 10, 10, 10, 10, 9,
    9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
    9, 9, 9, 9, 9, 9, 9, 9, 9, 9,
    9, 9, 9, 9, 9, 9, 9, 9, 8, 8,
    8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
    8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
    8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
    3, 3, 3, 3, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 0};
static const int32_t fe_logadd_table_size =
    (int32_t)(sizeof(fe_logadd_table) / sizeof(fe_logadd_table[0]));

int32_t sphinx_fe_log_add(int32_t x, int32_t y)
{
    int32_t d, r;

    if (x > y)
    {
        d = (x - y) >> (DEFAULT_RADIX - 8);
        r = x;
    }
    else
    {
        d = (y - x) >> (DEFAULT_RADIX - 8);
        r = y;
    }
    if (d > fe_logadd_table_size - 1)
        return r;
    else
    {
        r += ((int32_t)fe_logadd_table[d] << (DEFAULT_RADIX - 8));
        /*
        printf("%d + %d = %d | %f + %f = %f | %f + %f = %f\n",
               x, y, r, FIX2FLOAT(x), FIX2FLOAT(y), FIX2FLOAT(r),
               exp(FIX2FLOAT(x)), exp(FIX2FLOAT(y)), exp(FIX2FLOAT(r)));
*/
        return r;
    }
}

/* Table of log2(x/64)*(1<<DEFAULT_RADIX) */
static const uint16_t logtable[] = {
    0, 92, 182, 271, 358, 445, 530, 613, 696, 778,
    858, 937, 1016, 1093, 1169, 1244, 1319, 1392, 1465, 1536,
    1607, 1677, 1746, 1814, 1882, 1949, 2015, 2080, 2145, 2208,
    2272, 2334, 2396, 2457, 2518, 2578, 2637, 2696, 2754, 2812,
    2869, 2926, 2982, 3037, 3092, 3146, 3200, 3254, 3307, 3359,
    3412, 3463, 3514, 3565, 3615, 3665, 3715, 3764, 3812, 3861,
    3908, 3956, 4003, 4050};

int32_t sphinx_fixlog2(uint32_t x)
{
    uint32_t y;

    if (x == 0)
        return MIN_FIXLOG2;

    /* Get the exponent. */
    for (y = 31; y > 0; --y)
    {
        if (x & 0x80000000)
            break;
        x <<= 1;
    }
    y <<= DEFAULT_RADIX;
    /* Do a table lookup for the MSB of the mantissa. */
    x = (x >> 25) & 0x3f;

    return y + logtable[x];
}

int32_t sphinx_fixlog(uint32_t x)
{
    int32_t y;

    if (x == 0)
        return MIN_FIXLOG;

    y = sphinx_fixlog2(x);
    return FIXMUL(y, FIXLN_2);
}

int32_t sphinx_get_fixlog_rom_size(void)
{
    return (int32_t)(sizeof(logtable) + sizeof(fe_logadd_table));
}
