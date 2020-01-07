import numpy as np
import tensorflow as tf
from sleap.nn.architectures import upsampling


class UpsamplingTests(tf.test.TestCase):
    def test_intermediate_feature(self):
        intermediate_feature = upsampling.IntermediateFeature(
            tensor=tf.zeros((1, 1, 1, 1)), stride=4
        )
        self.assertEqual(intermediate_feature.scale, 0.25)

    def test_upsampling_stack(self):
        upsampling_stack = upsampling.UpsamplingStack(
            output_stride=4,
            upsampling_stride=2,
            transposed_conv=True,
            transposed_conv_batchnorm=True,
            refine_convs=1,
            refine_convs_batchnorm=True,
        )
        x, intermediate_feats = upsampling_stack.make_stack(
            tf.keras.Input((8, 8, 32)), current_stride=16
        )
        model = tf.keras.Model(tf.keras.utils.get_source_inputs(x), x)

        self.assertAllEqual(x.shape, (None, 32, 32, 64))
        self.assertEqual(len(intermediate_feats), 2)
        self.assertEqual(intermediate_feats[0].stride, 8)
        self.assertEqual(intermediate_feats[1].stride, 4)
        self.assertEqual(len(model.layers), 13)
        self.assertIsInstance(model.layers[1], tf.keras.layers.Conv2DTranspose)

    def test_upsampling_stack_upsampling_stride4(self):
        upsampling_stack = upsampling.UpsamplingStack(
            output_stride=4, upsampling_stride=4
        )
        x, intermediate_feats = upsampling_stack.make_stack(
            tf.keras.Input((8, 8, 32)), current_stride=16
        )

        self.assertAllEqual(x.shape, (None, 32, 32, 64))
        self.assertEqual(len(intermediate_feats), 1)

    def test_upsampling_stack_upsampling_interp(self):
        upsampling_stack = upsampling.UpsamplingStack(
            output_stride=8, upsampling_stride=2, transposed_conv=False
        )
        x, intermediate_feats = upsampling_stack.make_stack(
            tf.keras.Input((8, 8, 32)), current_stride=16
        )

        self.assertAllEqual(x.shape, (None, 16, 16, 64))
        model = tf.keras.Model(tf.keras.utils.get_source_inputs(x), x)
        self.assertIsInstance(model.layers[1], tf.keras.layers.UpSampling2D)

    def test_upsampling_stack_upsampling_skip(self):
        upsampling_stack = upsampling.UpsamplingStack(
            output_stride=2,
            upsampling_stride=2,
            skip_add=False,
            transposed_conv=True,
            transposed_conv_filters=16,
            refine_convs=0,
        )
        skip_sources = [
            upsampling.IntermediateFeature(
                tensor=tf.keras.Input((16, 16, 1)), stride=8
            ),
            upsampling.IntermediateFeature(
                tensor=tf.keras.Input((32, 32, 2)), stride=4
            ),
        ]
        x, intermediate_feats = upsampling_stack.make_stack(
            tf.keras.Input((8, 8, 32)), current_stride=16, skip_sources=skip_sources
        )
        model = tf.keras.Model(tf.keras.utils.get_source_inputs(x), x)

        self.assertAllEqual(x.shape, (None, 64, 64, 16))
        self.assertEqual(len(intermediate_feats), 3)
        self.assertIsInstance(model.layers[1], tf.keras.layers.Conv2DTranspose)
        self.assertIsInstance(model.layers[2], tf.keras.layers.BatchNormalization)
        self.assertIsInstance(model.layers[4], tf.keras.layers.Activation)
        self.assertIsInstance(model.layers[5], tf.keras.layers.Concatenate)
        self.assertAllEqual(model.layers[5].output.shape, (None, 16, 16, 17))

        self.assertIsInstance(model.layers[10], tf.keras.layers.Concatenate)
        self.assertAllEqual(model.layers[10].output.shape, (None, 32, 32, 18))

    def test_upsampling_stack_upsampling_add(self):
        upsampling_stack = upsampling.UpsamplingStack(
            output_stride=2,
            upsampling_stride=2,
            skip_add=True,
            transposed_conv=True,
            transposed_conv_filters=16,
            refine_convs=0,
        )
        skip_sources = [
            upsampling.IntermediateFeature(
                tensor=tf.keras.Input((16, 16, 1)), stride=8
            ),
            upsampling.IntermediateFeature(
                tensor=tf.keras.Input((32, 32, 2)), stride=4
            ),
        ]
        x, intermediate_feats = upsampling_stack.make_stack(
            tf.keras.Input((8, 8, 32)), current_stride=16, skip_sources=skip_sources
        )
        model = tf.keras.Model(tf.keras.utils.get_source_inputs(x), x)

        self.assertAllEqual(x.shape, (None, 64, 64, 16))
        self.assertEqual(len(intermediate_feats), 3)
        self.assertAllEqual(
            model.get_layer("upsample_s16_to_s8_skip_conv1x1").output.shape,
            (None, 16, 16, 16),
        )
        self.assertAllEqual(
            model.get_layer("upsample_s8_to_s4_skip_conv1x1").output.shape,
            (None, 32, 32, 16),
        )
        self.assertIsInstance(
            model.get_layer("upsample_s16_to_s8_skip_add"), tf.keras.layers.Add
        )