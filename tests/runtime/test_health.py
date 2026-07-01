from crypt.runtime.health import _okx_swap_ids


def test_okx_swap_ids_ignores_malformed_market_rows() -> None:
    response = {
        "data": [
            {"instId": "SOL-USDT-SWAP"},
            {"instId": None},
            {},
            "malformed",
        ]
    }

    assert _okx_swap_ids(response) == {"SOL-USDT-SWAP"}
