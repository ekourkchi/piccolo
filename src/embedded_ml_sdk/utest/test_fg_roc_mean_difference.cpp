#include "gtest/gtest.h"
#include "kbalgorithms.h"
#include "kb_typedefs.h"
#include "rb.h"
#include "kb_common.h"
#include "kb_utest_init.h"
#include <stdio.h>

#define NUM_ROWS 20
#define NUM_INPUT_COLS 1

static int16_t rb_inputs[NUM_INPUT_COLS * NUM_ROWS] =
    {0, 9, 5, -5, -9, 0, 9, 5, -5, -9, 0, 9, 5, -5, -9, 0, 9, 5, -5, -9};

static float expected_outputs[NUM_INPUT_COLS] = {-0.47368};

class FGROCMeanDifference : public testing::Test
{
protected:
    virtual void SetUp()
    {
        num_cols = NUM_INPUT_COLS;
        num_rows = NUM_ROWS;
        sg_index = 0;
        sg_length = num_rows;
        init_kb_model(&kb_model, &rb[0], sg_index, sg_length, rb_inputs, num_cols, num_rows);
        params.size =0;
        params.data[0] = 0;
        ret = 0;
    }
};

TEST_F(FGROCMeanDifference, kb_model_NULL_param_test)
{
    // kb_model is NULL
    ret = fg_roc_mean_difference(NULL, &cols_to_use, &params, pFV);
    ASSERT_EQ(0, ret);
}

TEST_F(FGROCMeanDifference, NULL_cols_to_use_param_test)
{
    ret = fg_roc_mean_difference(&kb_model, NULL, &params, pFV);
    ASSERT_EQ(0, ret);
}

TEST_F(FGROCMeanDifference, ZERO_num_cols_param_test)
{
   cols_to_use.size=0;
   ret  = fg_roc_mean_difference(&kb_model, &cols_to_use, &params, pFV);
    ASSERT_EQ(0, ret);
}

TEST_F(FGROCMeanDifference, NULL_feature_vector_test)
{
    ret = fg_roc_mean_difference(&kb_model, &cols_to_use, &params, NULL);
    ASSERT_EQ(0, ret);
}

TEST_F(FGROCMeanDifference, generate_features_test)
{
    ret = fg_roc_mean_difference(&kb_model, &cols_to_use, &params, pFV);
    ASSERT_EQ(num_cols, ret);
    float tolerance = 0.001f;
    if (ret == num_cols)
    {
        int icol;
        for (icol = 0; icol < cols_to_use.size; icol++)
        {
            printf("pFV[%d] = %f\n", icol, pFV[icol]);
            EXPECT_NEAR(pFV[icol], expected_outputs[icol], tolerance);
        }
    }
}
