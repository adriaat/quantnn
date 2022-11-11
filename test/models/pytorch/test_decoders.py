"""
Tests for quantnn.models.pytorch.decoders.
"""
import torch
from quantnn.packed_tensor import PackedTensor
from quantnn.models.pytorch.encoders import (
    SpatialEncoder,
    MultiInputSpatialEncoder
)
from quantnn.models.pytorch.decoders import (
    SpatialDecoder,
    SparseSpatialDecoder
)
from quantnn.models.pytorch.torchvision import ResNetBlockFactory
from quantnn.models.pytorch.aggregators import (
    LinearAggregatorFactory,
    SparseAggregatorFactory
)


def test_spatial_decoder():
    """
    Test that chaining an encoder and corresponding decoder reproduces
    output of the same spatial dimensions as the input.
    """
    block_factory = ResNetBlockFactory()
    encoder = SpatialEncoder(
        channels=1,
        stages=[4] * 4,
        channel_scaling=2,
        max_channels=8,
        block_factory=block_factory,
    )
    decoder = SpatialDecoder(
        channels=1,
        stages=[4] * 4,
        channel_scaling=2,
        max_channels=8,
        block_factory=block_factory,
        skip_connections=False
    )
    # Test forward without skip connections.
    x = torch.ones((1, 1, 32, 32))
    y = decoder(encoder(x))
    # Width and height should be reduced by 16.
    # Number of channels should be maximum.
    assert y.shape == (1, 1, 32, 32)

    decoder = SpatialDecoder(
        channels=1,
        stages=[4] * 4,
        channel_scaling=2,
        max_channels=8,
        block_factory=block_factory,
        skip_connections=True
    )
    # Test forward width skips returned.
    y = decoder(encoder(x, return_skips=True))
    # Number of outputs is number of stages + 1.
    assert y.shape == (1, 1, 32, 32)


def test_encoder_decoder_asymmetric():
    """
    Tests the chaining of a multi-input encoder and a decoder with
    skip connections.
    """
    block_factory = ResNetBlockFactory()
    aggregator_factory = LinearAggregatorFactory()
    input_channels = {
        1: 16,
        2: 32
    }
    encoder = MultiInputSpatialEncoder(
        input_channels=input_channels,
        channels=4,
        stages=[4] * 4,
        block_factory=block_factory,
        channel_scaling=2,
        max_channels=16,
        aggregator_factory=aggregator_factory
    )
    decoder = SpatialDecoder(
        channels=4,
        stages=[4] * 4,
        channel_scaling=2,
        max_channels=16,
        block_factory=block_factory,
        skip_connections=3
    )
    # Test forward without skip connections.
    x = [
        torch.ones((1, 16, 16, 16)),
        torch.ones((1, 32, 8, 8)),
    ]
    y = encoder(x, return_skips=True)
    y = decoder(y)
    assert y.shape == (1, 4, 32, 32)


def test_encoder_decoder_sparse():
    """
    Tests the chaining of a multi-input encoder and a decoder with
    potentially missing input.
    """
    block_factory = ResNetBlockFactory()
    aggregator_factory = SparseAggregatorFactory(
        LinearAggregatorFactory()
    )
    input_channels = {
        1: 16,
        2: 32
    }
    encoder = MultiInputSpatialEncoder(
        input_channels=input_channels,
        channels=4,
        stages=[4] * 4,
        block_factory=block_factory,
        channel_scaling=2,
        max_channels=16,
        aggregator_factory=aggregator_factory
    )
    decoder = SparseSpatialDecoder(
        channels=4,
        stages=[4] * 4,
        channel_scaling=2,
        max_channels=16,
        block_factory=block_factory,
        skip_connections=3
    )
    # Test forward without skip connections.
    x = [
        PackedTensor(
            torch.ones((0, 16, 16, 16)),
            batch_size=4,
            batch_indices=[]
        ),
        PackedTensor(
            torch.ones((1, 32, 8, 8)),
            batch_size=4,
            batch_indices=[0]
        )
    ]
    y = encoder(x, return_skips=True)
    y = decoder(y)
    assert y.shape == (1, 4, 32, 32)


def test_encoder_decoder_multi_scale_output():
    """
    Tests the chaining of a multi-input encoder and a decoder with
    potentially missing input.
    """
    block_factory = ResNetBlockFactory()
    aggregator_factory = SparseAggregatorFactory(
        LinearAggregatorFactory()
    )
    input_channels = {
        1: 16,
        2: 32
    }
    encoder = MultiInputSpatialEncoder(
        input_channels=input_channels,
        channels=4,
        stages=[4] * 4,
        block_factory=block_factory,
        channel_scaling=2,
        max_channels=16,
        aggregator_factory=aggregator_factory
    )
    decoder = SparseSpatialDecoder(
        channels=4,
        stages=[4] * 4,
        channel_scaling=2,
        max_channels=16,
        block_factory=block_factory,
        skip_connections=3,
        multi_scale_output=16
    )
    # Test forward without skip connections.
    x = [
        PackedTensor(
            torch.ones((0, 16, 16, 16)),
            batch_size=4,
            batch_indices=[]
        ),
        PackedTensor(
            torch.ones((1, 32, 8, 8)),
            batch_size=4,
            batch_indices=[0]
        )
    ]
    y = encoder(x, return_skips=True)
    y = decoder(y)
    assert len(y) == 4
    for y_i in y:
        assert y_i.shape[1] == 16
