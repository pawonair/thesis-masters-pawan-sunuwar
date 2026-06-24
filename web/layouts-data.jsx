// AUTO-GENERATED – do not hand-edit.
window.LAYOUT_DATA = {
    "1_Straight": {
        "name": "1_Straight",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "UP",
                "source": "signal2",
                "destination": "signal4",
                "approach": "seg3",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg3",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal2",
                    "signal4"
                ],
                "conflicts": []
            },
            "r1": {
                "id": "r1",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal1",
                "approach": "seg5",
                "terminal": "seg1",
                "destBlockSegs": [
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "path": [
                    "seg5",
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "signals": [
                    "signal3",
                    "signal1"
                ],
                "conflicts": []
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg3 · UP → signal4 (r0)",
                "route": "r0",
                "startSeg": "seg3"
            },
            {
                "value": "r1",
                "label": "seg5 · DOWN → signal1 (r1)",
                "route": "r1",
                "startSeg": "seg5"
            }
        ]
    },
    "2_Point": {
        "name": "2_Point",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "UP",
                "source": "signal2",
                "destination": "signal4",
                "approach": "seg3",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg3",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal2",
                    "signal4"
                ],
                "conflicts": [
                    "r1",
                    "r2",
                    "r3"
                ]
            },
            "r1": {
                "id": "r1",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal1",
                "approach": "seg5",
                "terminal": "seg1",
                "destBlockSegs": [
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "signals": [
                    "signal3",
                    "signal1"
                ],
                "conflicts": [
                    "r0",
                    "r2",
                    "r3"
                ]
            },
            "r2": {
                "id": "r2",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal7",
                "approach": "seg5",
                "terminal": "seg14",
                "destBlockSegs": [
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "signals": [
                    "signal3",
                    "signal7"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r3"
                ]
            },
            "r3": {
                "id": "r3",
                "dir": "UP",
                "source": "signal8",
                "destination": "signal4",
                "approach": "seg16",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg16",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal8",
                    "signal4"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r2"
                ]
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg3 · UP → signal4 (r0)",
                "route": "r0",
                "startSeg": "seg3"
            },
            {
                "value": "r1",
                "label": "seg5 · DOWN → signal1 (r1)",
                "route": "r1",
                "startSeg": "seg5"
            },
            {
                "value": "r2",
                "label": "seg5 · DOWN → signal7 (r2)",
                "route": "r2",
                "startSeg": "seg5"
            },
            {
                "value": "r3",
                "label": "seg16 · UP → signal4 (r3)",
                "route": "r3",
                "startSeg": "seg16"
            }
        ]
    },
    "3_Cross": {
        "name": "3_Cross",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal10",
                "approach": "seg7",
                "terminal": "seg20",
                "destBlockSegs": [
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "point5",
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "signals": [
                    "signal4",
                    "signal10"
                ],
                "conflicts": [
                    "r1",
                    "r2",
                    "r3",
                    "r4",
                    "r5"
                ]
            },
            "r1": {
                "id": "r1",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal6",
                "approach": "seg7",
                "terminal": "seg11",
                "destBlockSegs": [
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "signals": [
                    "signal4",
                    "signal6"
                ],
                "conflicts": [
                    "r0",
                    "r2",
                    "r3"
                ]
            },
            "r2": {
                "id": "r2",
                "dir": "DOWN",
                "source": "signal5",
                "destination": "signal3",
                "approach": "seg9",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg9",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal5",
                    "signal3"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r3"
                ]
            },
            "r3": {
                "id": "r3",
                "dir": "DOWN",
                "source": "signal9",
                "destination": "signal3",
                "approach": "seg18",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg18",
                    "point5",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal9",
                    "signal3"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r2",
                    "r4",
                    "r5"
                ]
            },
            "r4": {
                "id": "r4",
                "dir": "DOWN",
                "source": "signal9",
                "destination": "signal15",
                "approach": "seg18",
                "terminal": "seg29",
                "destBlockSegs": [
                    "seg27",
                    "seg28",
                    "seg29"
                ],
                "path": [
                    "seg18",
                    "point5",
                    "seg27",
                    "seg28",
                    "seg29"
                ],
                "signals": [
                    "signal9",
                    "signal15"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r5"
                ]
            },
            "r5": {
                "id": "r5",
                "dir": "UP",
                "source": "signal14",
                "destination": "signal10",
                "approach": "seg27",
                "terminal": "seg20",
                "destBlockSegs": [
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "path": [
                    "seg27",
                    "point5",
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "signals": [
                    "signal14",
                    "signal10"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r4"
                ]
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg7 · UP → signal10 (r0)",
                "route": "r0",
                "startSeg": "seg7"
            },
            {
                "value": "r1",
                "label": "seg7 · UP → signal6 (r1)",
                "route": "r1",
                "startSeg": "seg7"
            },
            {
                "value": "r2",
                "label": "seg9 · DOWN → signal3 (r2)",
                "route": "r2",
                "startSeg": "seg9"
            },
            {
                "value": "r3",
                "label": "seg18 · DOWN → signal3 (r3)",
                "route": "r3",
                "startSeg": "seg18"
            },
            {
                "value": "r4",
                "label": "seg18 · DOWN → signal15 (r4)",
                "route": "r4",
                "startSeg": "seg18"
            },
            {
                "value": "r5",
                "label": "seg27 · UP → signal10 (r5)",
                "route": "r5",
                "startSeg": "seg27"
            }
        ]
    },
    "4_Mini": {
        "name": "4_Mini",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "DOWN",
                "source": "signal1",
                "destination": "signal5",
                "approach": "seg1",
                "terminal": "seg9",
                "destBlockSegs": [
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "path": [
                    "seg1",
                    "point3",
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "signals": [
                    "signal1",
                    "signal5"
                ],
                "conflicts": [
                    "r4",
                    "r5",
                    "r6"
                ]
            },
            "r1": {
                "id": "r1",
                "dir": "UP",
                "source": "signal2",
                "destination": "signal4",
                "approach": "seg3",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg3",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal2",
                    "signal4"
                ],
                "conflicts": [
                    "r2",
                    "r3",
                    "r7"
                ]
            },
            "r2": {
                "id": "r2",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal1",
                "approach": "seg5",
                "terminal": "seg1",
                "destBlockSegs": [
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "signals": [
                    "signal3",
                    "signal1"
                ],
                "conflicts": [
                    "r1",
                    "r3",
                    "r4",
                    "r7"
                ]
            },
            "r3": {
                "id": "r3",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal7",
                "approach": "seg5",
                "terminal": "seg14",
                "destBlockSegs": [
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "signals": [
                    "signal3",
                    "signal7"
                ],
                "conflicts": [
                    "r1",
                    "r2",
                    "r5",
                    "r7"
                ]
            },
            "r4": {
                "id": "r4",
                "dir": "UP",
                "source": "signal6",
                "destination": "signal2",
                "approach": "seg11",
                "terminal": "seg3",
                "destBlockSegs": [
                    "seg1",
                    "seg2",
                    "seg3"
                ],
                "path": [
                    "seg11",
                    "point3",
                    "seg1",
                    "seg2",
                    "seg3"
                ],
                "signals": [
                    "signal6",
                    "signal2"
                ],
                "conflicts": [
                    "r0",
                    "r2",
                    "r5",
                    "r6"
                ]
            },
            "r5": {
                "id": "r5",
                "dir": "UP",
                "source": "signal6",
                "destination": "signal8",
                "approach": "seg11",
                "terminal": "seg16",
                "destBlockSegs": [
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "path": [
                    "seg11",
                    "point3",
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "signals": [
                    "signal6",
                    "signal8"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r4",
                    "r6"
                ]
            },
            "r6": {
                "id": "r6",
                "dir": "DOWN",
                "source": "signal7",
                "destination": "signal5",
                "approach": "seg14",
                "terminal": "seg9",
                "destBlockSegs": [
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "path": [
                    "seg14",
                    "point3",
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "signals": [
                    "signal7",
                    "signal5"
                ],
                "conflicts": [
                    "r0",
                    "r4",
                    "r5"
                ]
            },
            "r7": {
                "id": "r7",
                "dir": "UP",
                "source": "signal8",
                "destination": "signal4",
                "approach": "seg16",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg16",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal8",
                    "signal4"
                ],
                "conflicts": [
                    "r1",
                    "r2",
                    "r3"
                ]
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg1 · DOWN → signal5 (r0)",
                "route": "r0",
                "startSeg": "seg1"
            },
            {
                "value": "r1",
                "label": "seg3 · UP → signal4 (r1)",
                "route": "r1",
                "startSeg": "seg3"
            },
            {
                "value": "r2",
                "label": "seg5 · DOWN → signal1 (r2)",
                "route": "r2",
                "startSeg": "seg5"
            },
            {
                "value": "r3",
                "label": "seg5 · DOWN → signal7 (r3)",
                "route": "r3",
                "startSeg": "seg5"
            },
            {
                "value": "r4",
                "label": "seg11 · UP → signal2 (r4)",
                "route": "r4",
                "startSeg": "seg11"
            },
            {
                "value": "r5",
                "label": "seg11 · UP → signal8 (r5)",
                "route": "r5",
                "startSeg": "seg11"
            },
            {
                "value": "r6",
                "label": "seg14 · DOWN → signal5 (r6)",
                "route": "r6",
                "startSeg": "seg14"
            },
            {
                "value": "r7",
                "label": "seg16 · UP → signal4 (r7)",
                "route": "r7",
                "startSeg": "seg16"
            }
        ]
    },
    "5_Fork": {
        "name": "5_Fork",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "UP",
                "source": "signal10",
                "destination": "signal8",
                "approach": "seg20",
                "terminal": "seg16",
                "destBlockSegs": [
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "path": [
                    "seg20",
                    "point6",
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "signals": [
                    "signal10",
                    "signal8"
                ],
                "conflicts": [
                    "r1",
                    "r5",
                    "r7"
                ]
            },
            "r1": {
                "id": "r1",
                "dir": "UP",
                "source": "signal10",
                "destination": "signal12",
                "approach": "seg20",
                "terminal": "seg25",
                "destBlockSegs": [
                    "seg23",
                    "seg24",
                    "seg25"
                ],
                "path": [
                    "seg20",
                    "point6",
                    "seg23",
                    "seg24",
                    "seg25"
                ],
                "signals": [
                    "signal10",
                    "signal12"
                ],
                "conflicts": [
                    "r0",
                    "r5",
                    "r7"
                ]
            },
            "r2": {
                "id": "r2",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal10",
                "approach": "seg7",
                "terminal": "seg20",
                "destBlockSegs": [
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "signals": [
                    "signal4",
                    "signal10"
                ],
                "conflicts": [
                    "r3",
                    "r4",
                    "r5",
                    "r6",
                    "r7"
                ]
            },
            "r3": {
                "id": "r3",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal6",
                "approach": "seg7",
                "terminal": "seg11",
                "destBlockSegs": [
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "signals": [
                    "signal4",
                    "signal6"
                ],
                "conflicts": [
                    "r2",
                    "r4",
                    "r6"
                ]
            },
            "r4": {
                "id": "r4",
                "dir": "DOWN",
                "source": "signal5",
                "destination": "signal3",
                "approach": "seg9",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg9",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal5",
                    "signal3"
                ],
                "conflicts": [
                    "r2",
                    "r3",
                    "r6"
                ]
            },
            "r5": {
                "id": "r5",
                "dir": "DOWN",
                "source": "signal7",
                "destination": "signal9",
                "approach": "seg14",
                "terminal": "seg18",
                "destBlockSegs": [
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "path": [
                    "seg14",
                    "point6",
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "signals": [
                    "signal7",
                    "signal9"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r2",
                    "r7"
                ]
            },
            "r6": {
                "id": "r6",
                "dir": "DOWN",
                "source": "signal9",
                "destination": "signal3",
                "approach": "seg18",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg18",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal9",
                    "signal3"
                ],
                "conflicts": [
                    "r2",
                    "r3",
                    "r4"
                ]
            },
            "r7": {
                "id": "r7",
                "dir": "DOWN",
                "source": "signal11",
                "destination": "signal9",
                "approach": "seg23",
                "terminal": "seg18",
                "destBlockSegs": [
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "path": [
                    "seg23",
                    "point6",
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "signals": [
                    "signal11",
                    "signal9"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r2",
                    "r5"
                ]
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg20 · UP → signal8 (r0)",
                "route": "r0",
                "startSeg": "seg20"
            },
            {
                "value": "r1",
                "label": "seg20 · UP → signal12 (r1)",
                "route": "r1",
                "startSeg": "seg20"
            },
            {
                "value": "r2",
                "label": "seg7 · UP → signal10 (r2)",
                "route": "r2",
                "startSeg": "seg7"
            },
            {
                "value": "r3",
                "label": "seg7 · UP → signal6 (r3)",
                "route": "r3",
                "startSeg": "seg7"
            },
            {
                "value": "r4",
                "label": "seg9 · DOWN → signal3 (r4)",
                "route": "r4",
                "startSeg": "seg9"
            },
            {
                "value": "r5",
                "label": "seg14 · DOWN → signal9 (r5)",
                "route": "r5",
                "startSeg": "seg14"
            },
            {
                "value": "r6",
                "label": "seg18 · DOWN → signal3 (r6)",
                "route": "r6",
                "startSeg": "seg18"
            },
            {
                "value": "r7",
                "label": "seg23 · DOWN → signal9 (r7)",
                "route": "r7",
                "startSeg": "seg23"
            }
        ]
    },
    "6_Twist": {
        "name": "6_Twist",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "UP",
                "source": "signal2",
                "destination": "signal4",
                "approach": "seg3",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg3",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal2",
                    "signal4"
                ],
                "conflicts": [
                    "r1",
                    "r2",
                    "r5",
                    "r6",
                    "r7"
                ]
            },
            "r1": {
                "id": "r1",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal1",
                "approach": "seg5",
                "terminal": "seg1",
                "destBlockSegs": [
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "signals": [
                    "signal3",
                    "signal1"
                ],
                "conflicts": [
                    "r0",
                    "r2",
                    "r6"
                ]
            },
            "r2": {
                "id": "r2",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal7",
                "approach": "seg5",
                "terminal": "seg14",
                "destBlockSegs": [
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "signals": [
                    "signal3",
                    "signal7"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r6"
                ]
            },
            "r3": {
                "id": "r3",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal10",
                "approach": "seg7",
                "terminal": "seg20",
                "destBlockSegs": [
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "signals": [
                    "signal4",
                    "signal10"
                ],
                "conflicts": [
                    "r4",
                    "r5",
                    "r7"
                ]
            },
            "r4": {
                "id": "r4",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal6",
                "approach": "seg7",
                "terminal": "seg11",
                "destBlockSegs": [
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "signals": [
                    "signal4",
                    "signal6"
                ],
                "conflicts": [
                    "r3",
                    "r5",
                    "r7"
                ]
            },
            "r5": {
                "id": "r5",
                "dir": "DOWN",
                "source": "signal5",
                "destination": "signal3",
                "approach": "seg9",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg9",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal5",
                    "signal3"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r4",
                    "r6",
                    "r7"
                ]
            },
            "r6": {
                "id": "r6",
                "dir": "UP",
                "source": "signal8",
                "destination": "signal4",
                "approach": "seg16",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg16",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal8",
                    "signal4"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r2",
                    "r5",
                    "r7"
                ]
            },
            "r7": {
                "id": "r7",
                "dir": "DOWN",
                "source": "signal9",
                "destination": "signal3",
                "approach": "seg18",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg18",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal9",
                    "signal3"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r4",
                    "r5",
                    "r6"
                ]
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg3 · UP → signal4 (r0)",
                "route": "r0",
                "startSeg": "seg3"
            },
            {
                "value": "r1",
                "label": "seg5 · DOWN → signal1 (r1)",
                "route": "r1",
                "startSeg": "seg5"
            },
            {
                "value": "r2",
                "label": "seg5 · DOWN → signal7 (r2)",
                "route": "r2",
                "startSeg": "seg5"
            },
            {
                "value": "r3",
                "label": "seg7 · UP → signal10 (r3)",
                "route": "r3",
                "startSeg": "seg7"
            },
            {
                "value": "r4",
                "label": "seg7 · UP → signal6 (r4)",
                "route": "r4",
                "startSeg": "seg7"
            },
            {
                "value": "r5",
                "label": "seg9 · DOWN → signal3 (r5)",
                "route": "r5",
                "startSeg": "seg9"
            },
            {
                "value": "r6",
                "label": "seg16 · UP → signal4 (r6)",
                "route": "r6",
                "startSeg": "seg16"
            },
            {
                "value": "r7",
                "label": "seg18 · DOWN → signal3 (r7)",
                "route": "r7",
                "startSeg": "seg18"
            }
        ]
    },
    "7_Lite": {
        "name": "7_Lite",
        "routes": {
            "r0": {
                "id": "r0",
                "dir": "UP",
                "source": "signal8",
                "destination": "signal4",
                "approach": "seg16",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg16",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal8",
                    "signal4"
                ],
                "conflicts": [
                    "r1",
                    "r3",
                    "r4",
                    "r5",
                    "r9"
                ]
            },
            "r1": {
                "id": "r1",
                "dir": "DOWN",
                "source": "signal9",
                "destination": "signal3",
                "approach": "seg18",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg18",
                    "point5",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal9",
                    "signal3"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r7",
                    "r8",
                    "r9",
                    "r15"
                ]
            },
            "r2": {
                "id": "r2",
                "dir": "DOWN",
                "source": "signal1",
                "destination": "signal5",
                "approach": "seg1",
                "terminal": "seg9",
                "destBlockSegs": [
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "path": [
                    "seg1",
                    "point3",
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "signals": [
                    "signal1",
                    "signal5"
                ],
                "conflicts": [
                    "r8",
                    "r10",
                    "r11",
                    "r13"
                ]
            },
            "r3": {
                "id": "r3",
                "dir": "UP",
                "source": "signal2",
                "destination": "signal4",
                "approach": "seg3",
                "terminal": "seg7",
                "destBlockSegs": [
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "path": [
                    "seg3",
                    "point1",
                    "seg5",
                    "seg6",
                    "seg7"
                ],
                "signals": [
                    "signal2",
                    "signal4"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r4",
                    "r5",
                    "r9"
                ]
            },
            "r4": {
                "id": "r4",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal1",
                "approach": "seg5",
                "terminal": "seg1",
                "destBlockSegs": [
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg3",
                    "seg2",
                    "seg1"
                ],
                "signals": [
                    "signal3",
                    "signal1"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r5",
                    "r11"
                ]
            },
            "r5": {
                "id": "r5",
                "dir": "DOWN",
                "source": "signal3",
                "destination": "signal7",
                "approach": "seg5",
                "terminal": "seg14",
                "destBlockSegs": [
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "path": [
                    "seg5",
                    "point1",
                    "seg16",
                    "seg15",
                    "seg14"
                ],
                "signals": [
                    "signal3",
                    "signal7"
                ],
                "conflicts": [
                    "r0",
                    "r3",
                    "r4",
                    "r6",
                    "r10"
                ]
            },
            "r6": {
                "id": "r6",
                "dir": "UP",
                "source": "signal10",
                "destination": "signal8",
                "approach": "seg20",
                "terminal": "seg16",
                "destBlockSegs": [
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "path": [
                    "seg20",
                    "point6",
                    "point4",
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "signals": [
                    "signal10",
                    "signal8"
                ],
                "conflicts": [
                    "r5",
                    "r10",
                    "r12",
                    "r13",
                    "r14"
                ]
            },
            "r7": {
                "id": "r7",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal10",
                "approach": "seg7",
                "terminal": "seg20",
                "destBlockSegs": [
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "point5",
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "signals": [
                    "signal4",
                    "signal10"
                ],
                "conflicts": [
                    "r1",
                    "r8",
                    "r9",
                    "r12",
                    "r14",
                    "r15"
                ]
            },
            "r8": {
                "id": "r8",
                "dir": "UP",
                "source": "signal4",
                "destination": "signal6",
                "approach": "seg7",
                "terminal": "seg11",
                "destBlockSegs": [
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "path": [
                    "seg7",
                    "point2",
                    "seg9",
                    "seg10",
                    "seg11"
                ],
                "signals": [
                    "signal4",
                    "signal6"
                ],
                "conflicts": [
                    "r1",
                    "r2",
                    "r7",
                    "r9",
                    "r13"
                ]
            },
            "r9": {
                "id": "r9",
                "dir": "DOWN",
                "source": "signal5",
                "destination": "signal3",
                "approach": "seg9",
                "terminal": "seg5",
                "destBlockSegs": [
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "path": [
                    "seg9",
                    "point2",
                    "seg7",
                    "seg6",
                    "seg5"
                ],
                "signals": [
                    "signal5",
                    "signal3"
                ],
                "conflicts": [
                    "r0",
                    "r1",
                    "r3",
                    "r7",
                    "r8"
                ]
            },
            "r10": {
                "id": "r10",
                "dir": "UP",
                "source": "signal6",
                "destination": "signal8",
                "approach": "seg11",
                "terminal": "seg16",
                "destBlockSegs": [
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "path": [
                    "seg11",
                    "point3",
                    "point4",
                    "seg14",
                    "seg15",
                    "seg16"
                ],
                "signals": [
                    "signal6",
                    "signal8"
                ],
                "conflicts": [
                    "r2",
                    "r5",
                    "r6",
                    "r11",
                    "r12",
                    "r13"
                ]
            },
            "r11": {
                "id": "r11",
                "dir": "UP",
                "source": "signal6",
                "destination": "signal2",
                "approach": "seg11",
                "terminal": "seg3",
                "destBlockSegs": [
                    "seg1",
                    "seg2",
                    "seg3"
                ],
                "path": [
                    "seg11",
                    "point3",
                    "seg1",
                    "seg2",
                    "seg3"
                ],
                "signals": [
                    "signal6",
                    "signal2"
                ],
                "conflicts": [
                    "r2",
                    "r4",
                    "r10",
                    "r13"
                ]
            },
            "r12": {
                "id": "r12",
                "dir": "DOWN",
                "source": "signal7",
                "destination": "signal9",
                "approach": "seg14",
                "terminal": "seg18",
                "destBlockSegs": [
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "path": [
                    "seg14",
                    "point4",
                    "point6",
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "signals": [
                    "signal7",
                    "signal9"
                ],
                "conflicts": [
                    "r6",
                    "r7",
                    "r10",
                    "r13",
                    "r14",
                    "r15"
                ]
            },
            "r13": {
                "id": "r13",
                "dir": "DOWN",
                "source": "signal7",
                "destination": "signal5",
                "approach": "seg14",
                "terminal": "seg9",
                "destBlockSegs": [
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "path": [
                    "seg14",
                    "point4",
                    "point3",
                    "seg11",
                    "seg10",
                    "seg9"
                ],
                "signals": [
                    "signal7",
                    "signal5"
                ],
                "conflicts": [
                    "r2",
                    "r6",
                    "r8",
                    "r10",
                    "r11",
                    "r12"
                ]
            },
            "r14": {
                "id": "r14",
                "dir": "DOWN",
                "source": "signal11",
                "destination": "signal9",
                "approach": "seg23",
                "terminal": "seg18",
                "destBlockSegs": [
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "path": [
                    "seg23",
                    "point7",
                    "point6",
                    "seg20",
                    "seg19",
                    "seg18"
                ],
                "signals": [
                    "signal11",
                    "signal9"
                ],
                "conflicts": [
                    "r6",
                    "r7",
                    "r12",
                    "r15"
                ]
            },
            "r15": {
                "id": "r15",
                "dir": "DOWN",
                "source": "signal14",
                "destination": "signal10",
                "approach": "seg27",
                "terminal": "seg20",
                "destBlockSegs": [
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "path": [
                    "seg27",
                    "point5",
                    "seg18",
                    "seg19",
                    "seg20"
                ],
                "signals": [
                    "signal14",
                    "signal10"
                ],
                "conflicts": [
                    "r1",
                    "r7",
                    "r12",
                    "r14"
                ]
            }
        },
        "startOptions": [
            {
                "value": "r0",
                "label": "seg16 · UP → signal4 (r0)",
                "route": "r0",
                "startSeg": "seg16"
            },
            {
                "value": "r1",
                "label": "seg18 · DOWN → signal3 (r1)",
                "route": "r1",
                "startSeg": "seg18"
            },
            {
                "value": "r2",
                "label": "seg1 · DOWN → signal5 (r2)",
                "route": "r2",
                "startSeg": "seg1"
            },
            {
                "value": "r3",
                "label": "seg3 · UP → signal4 (r3)",
                "route": "r3",
                "startSeg": "seg3"
            },
            {
                "value": "r4",
                "label": "seg5 · DOWN → signal1 (r4)",
                "route": "r4",
                "startSeg": "seg5"
            },
            {
                "value": "r5",
                "label": "seg5 · DOWN → signal7 (r5)",
                "route": "r5",
                "startSeg": "seg5"
            },
            {
                "value": "r6",
                "label": "seg20 · UP → signal8 (r6)",
                "route": "r6",
                "startSeg": "seg20"
            },
            {
                "value": "r7",
                "label": "seg7 · UP → signal10 (r7)",
                "route": "r7",
                "startSeg": "seg7"
            },
            {
                "value": "r8",
                "label": "seg7 · UP → signal6 (r8)",
                "route": "r8",
                "startSeg": "seg7"
            },
            {
                "value": "r9",
                "label": "seg9 · DOWN → signal3 (r9)",
                "route": "r9",
                "startSeg": "seg9"
            },
            {
                "value": "r10",
                "label": "seg11 · UP → signal8 (r10)",
                "route": "r10",
                "startSeg": "seg11"
            },
            {
                "value": "r11",
                "label": "seg11 · UP → signal2 (r11)",
                "route": "r11",
                "startSeg": "seg11"
            },
            {
                "value": "r12",
                "label": "seg14 · DOWN → signal9 (r12)",
                "route": "r12",
                "startSeg": "seg14"
            },
            {
                "value": "r13",
                "label": "seg14 · DOWN → signal5 (r13)",
                "route": "r13",
                "startSeg": "seg14"
            },
            {
                "value": "r14",
                "label": "seg23 · DOWN → signal9 (r14)",
                "route": "r14",
                "startSeg": "seg23"
            },
            {
                "value": "r15",
                "label": "seg27 · DOWN → signal10 (r15)",
                "route": "r15",
                "startSeg": "seg27"
            }
        ]
    }
};
