"""Test for vehicleFunLearnInfo parsing on the Vehicle model.

Live shape captured from a Sealion 7 Comfort 2024 EU — 46 keys on the
getVehicles response top level, values tri-state per the issue body
(``0`` absent / ``1`` present / ``-1`` not applicable).
"""

from __future__ import annotations

from pybyd.models.vehicle import Vehicle


def test_vehicle_fun_learn_info_parses_from_camel_case_payload():
    """Pydantic alias_generator handles the camelCase API key."""
    vehicle = Vehicle.model_validate(
        {
            "vin": "TESTV1N0000000000",
            "modelName": "SEALION 7",
            "vehicleFunLearnInfo": {
                "openWindowLearnInfo": 1,
                "openWindow499LearnInfo": 1,
                "batteryHeating": 0,
                "refrigeratorLearnInfo": -1,
                "trunkLearnInfo": 1,
            },
        }
    )
    assert vehicle.vehicle_fun_learn_info == {
        "openWindowLearnInfo": 1,
        "openWindow499LearnInfo": 1,
        "batteryHeating": 0,
        "refrigeratorLearnInfo": -1,
        "trunkLearnInfo": 1,
    }


def test_vehicle_fun_learn_info_defaults_to_empty_dict():
    """Missing field doesn't break model construction."""
    vehicle = Vehicle.model_validate({"vin": "TESTV1N0000000000"})
    assert vehicle.vehicle_fun_learn_info == {}
