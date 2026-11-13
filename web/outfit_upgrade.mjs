const revision = {
  "workflow": "6e6994c0-ed93-47da-9efb-53a0b034b801",
  "nodes": [
    {
      "id": 334,
      "type": "PrimitiveBoolean",
      "pos": [
        2480,
        1510
      ],
      "size": [
        430,
        66
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "允许新衣改变原轮廓",
      "widgets_values": [
        true
      ],
      "color": "#294942",
      "bgcolor": "#22352f",
      "inputs": [
        {
          "name": "value",
          "type": "BOOLEAN",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "BOOLEAN",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "PrimitiveBoolean",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 335,
      "type": "ComfySwitchNode",
      "pos": [
        2480,
        1575
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "未手绘人物时采用选定范围",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 336,
      "type": "ComfySwitchNode",
      "pos": [
        2480,
        1640
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "按人物范围适配新轮廓",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 337,
      "type": "ComfySwitchNode",
      "pos": [
        2480,
        1705
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "按原图适配选中单品",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 338,
      "type": "ComfySwitchNode",
      "pos": [
        2480,
        1770
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "联合编辑使用所选部位指令",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 339,
      "type": "PrimitiveStringMultiline",
      "pos": [
        2850,
        1510
      ],
      "size": [
        310,
        110
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "高级 · 本次重点处理",
      "widgets_values": [
        ""
      ],
      "inputs": [
        {
          "name": "value",
          "type": "STRING",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "STRING",
          "type": "STRING",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "PrimitiveStringMultiline",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 340,
      "type": "StringConcatenate",
      "pos": [
        2850,
        1575
      ],
      "size": [
        325,
        110
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "合并本次修复要求",
      "widgets_values": [
        "",
        "",
        "\n"
      ],
      "inputs": [
        {
          "name": "string_a",
          "type": "STRING",
          "widget": {
            "name": "string_a"
          },
          "link": null
        },
        {
          "name": "string_b",
          "type": "STRING",
          "widget": {
            "name": "string_b"
          },
          "link": null
        },
        {
          "name": "delimiter",
          "type": "STRING",
          "widget": {
            "name": "delimiter"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "STRING",
          "type": "STRING",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "StringConcatenate",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 341,
      "type": "DapaoOutfitRegions",
      "pos": [
        2850,
        1640
      ],
      "size": [
        340,
        310
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "独立取件 · 优先参考图手绘",
      "widgets_values": [
        0,
        0,
        0.05
      ],
      "inputs": [
        {
          "name": "人物",
          "type": "IMAGE",
          "link": null
        },
        {
          "name": "服装",
          "type": "IMAGE",
          "link": null
        },
        {
          "name": "人物自动",
          "type": "MASK",
          "link": null
        },
        {
          "name": "服装自动",
          "type": "MASK",
          "link": null
        },
        {
          "name": "人物手绘",
          "type": "MASK",
          "link": null
        },
        {
          "name": "服装手绘",
          "type": "MASK",
          "link": null
        },
        {
          "name": "外扩像素",
          "type": "INT",
          "widget": {
            "name": "外扩像素"
          },
          "link": null
        },
        {
          "name": "羽化像素",
          "type": "INT",
          "widget": {
            "name": "羽化像素"
          },
          "link": null
        },
        {
          "name": "上下文比例",
          "type": "FLOAT",
          "widget": {
            "name": "上下文比例"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "人物局部",
          "type": "IMAGE",
          "links": []
        },
        {
          "name": "服装净图",
          "type": "IMAGE",
          "links": []
        },
        {
          "name": "贴回遮罩",
          "type": "MASK",
          "links": []
        },
        {
          "name": "左",
          "type": "INT",
          "links": []
        },
        {
          "name": "上",
          "type": "INT",
          "links": []
        },
        {
          "name": "原宽",
          "type": "INT",
          "links": []
        },
        {
          "name": "原高",
          "type": "INT",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "DapaoOutfitRegions",
        "cnr_id": "Dapao-Toolbox"
      }
    },
    {
      "id": 342,
      "type": "ComfySwitchNode",
      "pos": [
        2850,
        1705
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "服装原图或手绘单品",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "IMAGE",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "IMAGE",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "IMAGE",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 343,
      "type": "PrimitiveBoolean",
      "pos": [
        2850,
        1770
      ],
      "size": [
        430,
        66
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "单个小件 · 先放大参考",
      "widgets_values": [
        false
      ],
      "color": "#294942",
      "bgcolor": "#22352f",
      "inputs": [
        {
          "name": "value",
          "type": "BOOLEAN",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "BOOLEAN",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "PrimitiveBoolean",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 344,
      "type": "ComfySwitchNode",
      "pos": [
        2850,
        1835
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "小件能定位时使用放大参考",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "IMAGE",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "IMAGE",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "IMAGE",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 345,
      "type": "ComfySwitchNode",
      "pos": [
        2850,
        1900
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "按部位换装才启用小件参考",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 346,
      "type": "ThresholdMask",
      "pos": [
        3310,
        1510
      ],
      "size": [
        260,
        84
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "人物手绘 · 同一阈值判断有效像素",
      "widgets_values": [
        0.1
      ],
      "inputs": [
        {
          "name": "mask",
          "type": "MASK",
          "link": null
        },
        {
          "name": "value",
          "type": "FLOAT",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "MASK",
          "type": "MASK",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ThresholdMask",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 347,
      "type": "ThresholdMask",
      "pos": [
        3310,
        1575
      ],
      "size": [
        260,
        84
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "参考手绘 · 同一阈值判断有效像素",
      "widgets_values": [
        0.1
      ],
      "inputs": [
        {
          "name": "mask",
          "type": "MASK",
          "link": null
        },
        {
          "name": "value",
          "type": "FLOAT",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "MASK",
          "type": "MASK",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ThresholdMask",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 348,
      "type": "ThresholdMask",
      "pos": [
        3310,
        1640
      ],
      "size": [
        260,
        84
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "人物自动 · 同一阈值判断有效像素",
      "widgets_values": [
        0.1
      ],
      "inputs": [
        {
          "name": "mask",
          "type": "MASK",
          "link": null
        },
        {
          "name": "value",
          "type": "FLOAT",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "MASK",
          "type": "MASK",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ThresholdMask",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 349,
      "type": "ThresholdMask",
      "pos": [
        3310,
        1705
      ],
      "size": [
        260,
        84
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "参考自动 · 同一阈值判断有效像素",
      "widgets_values": [
        0.1
      ],
      "inputs": [
        {
          "name": "mask",
          "type": "MASK",
          "link": null
        },
        {
          "name": "value",
          "type": "FLOAT",
          "widget": {
            "name": "value"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "MASK",
          "type": "MASK",
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ThresholdMask",
        "cnr_id": "comfy-core"
      }
    },
    {
      "id": 350,
      "type": "ComfySwitchNode",
      "pos": [
        3310,
        1770
      ],
      "size": [
        320,
        135
      ],
      "flags": {
        "collapsed": true
      },
      "mode": 0,
      "title": "小件参考未定位时启用看图",
      "widgets_values": [
        false
      ],
      "inputs": [
        {
          "name": "on_false",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "on_true",
          "shape": 7,
          "type": "BOOLEAN",
          "link": null
        },
        {
          "name": "switch",
          "type": "BOOLEAN",
          "widget": {
            "name": "switch"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "name": "output",
          "type": "BOOLEAN",
          "slot_index": 0,
          "links": []
        }
      ],
      "properties": {
        "Node name for S&R": "ComfySwitchNode",
        "cnr_id": "comfy-core"
      }
    }
  ],
  "links": [
    [
      320,
      0,
      335,
      0,
      null
    ],
    [
      322,
      0,
      335,
      2,
      null
    ],
    [
      320,
      0,
      336,
      0,
      null
    ],
    [
      335,
      0,
      336,
      2,
      null
    ],
    [
      326,
      0,
      337,
      0,
      null
    ],
    [
      319,
      0,
      337,
      1,
      null
    ],
    [
      336,
      0,
      337,
      2,
      null
    ],
    [
      337,
      0,
      307,
      2,
      [
        326,
        0
      ]
    ],
    [
      337,
      0,
      308,
      2,
      [
        326,
        0
      ]
    ],
    [
      337,
      0,
      310,
      2,
      [
        326,
        0
      ]
    ],
    [
      328,
      0,
      338,
      0,
      null
    ],
    [
      336,
      0,
      338,
      2,
      null
    ],
    [
      338,
      0,
      329,
      2,
      [
        328,
        0
      ]
    ],
    [
      338,
      0,
      330,
      2,
      [
        328,
        0
      ]
    ],
    [
      338,
      0,
      331,
      2,
      [
        328,
        0
      ]
    ],
    [
      338,
      0,
      333,
      2,
      [
        328,
        0
      ]
    ],
    [
      340,
      0,
      22,
      1,
      [
        309,
        0
      ]
    ],
    [
      340,
      0,
      24,
      0,
      [
        309,
        0
      ]
    ],
    [
      340,
      0,
      332,
      0,
      [
        309,
        0
      ]
    ],
    [
      340,
      0,
      333,
      0,
      [
        309,
        0
      ]
    ],
    [
      309,
      0,
      340,
      0,
      null
    ],
    [
      339,
      0,
      340,
      1,
      null
    ],
    [
      2,
      0,
      341,
      0,
      null
    ],
    [
      2,
      0,
      341,
      1,
      null
    ],
    [
      316,
      0,
      341,
      2,
      null
    ],
    [
      341,
      1,
      342,
      0,
      null
    ],
    [
      324,
      0,
      342,
      2,
      null
    ],
    [
      342,
      0,
      308,
      1,
      [
        2,
        0
      ]
    ],
    [
      342,
      0,
      331,
      1,
      [
        2,
        0
      ]
    ],
    [
      334,
      0,
      335,
      1,
      null
    ],
    [
      319,
      0,
      336,
      1,
      null
    ],
    [
      343,
      0,
      345,
      0,
      null
    ],
    [
      320,
      0,
      345,
      1,
      null
    ],
    [
      301,
      0,
      345,
      2,
      null
    ],
    [
      2,
      0,
      344,
      0,
      null
    ],
    [
      341,
      1,
      344,
      1,
      null
    ],
    [
      345,
      0,
      344,
      2,
      null
    ],
    [
      317,
      0,
      341,
      3,
      null
    ],
    [
      344,
      0,
      342,
      1,
      null
    ],
    [
      1,
      1,
      346,
      0,
      null
    ],
    [
      346,
      0,
      14,
      4,
      [
        1,
        1
      ]
    ],
    [
      346,
      0,
      160,
      2,
      [
        1,
        1
      ]
    ],
    [
      346,
      0,
      322,
      0,
      [
        1,
        1
      ]
    ],
    [
      2,
      1,
      347,
      0,
      null
    ],
    [
      347,
      0,
      14,
      5,
      [
        2,
        1
      ]
    ],
    [
      347,
      0,
      324,
      0,
      [
        2,
        1
      ]
    ],
    [
      347,
      0,
      341,
      4,
      null
    ],
    [
      347,
      0,
      341,
      5,
      null
    ],
    [
      13,
      0,
      348,
      0,
      null
    ],
    [
      348,
      0,
      160,
      1,
      [
        13,
        0
      ]
    ],
    [
      348,
      0,
      321,
      0,
      [
        13,
        0
      ]
    ],
    [
      12,
      0,
      349,
      0,
      null
    ],
    [
      349,
      0,
      315,
      0,
      [
        12,
        0
      ]
    ],
    [
      349,
      0,
      317,
      0,
      [
        12,
        0
      ]
    ],
    [
      320,
      0,
      350,
      0,
      null
    ],
    [
      325,
      0,
      350,
      1,
      null
    ],
    [
      345,
      0,
      350,
      2,
      null
    ],
    [
      350,
      0,
      338,
      1,
      null
    ]
  ],
  "anchors": {
    "320": "PrimitiveBoolean",
    "322": "easy isMaskEmpty",
    "326": "ComfySwitchNode",
    "319": "PrimitiveBoolean",
    "307": "ComfySwitchNode",
    "308": "ComfySwitchNode",
    "310": "ComfySwitchNode",
    "328": "ComfySwitchNode",
    "329": "ComfySwitchNode",
    "330": "ComfySwitchNode",
    "331": "ComfySwitchNode",
    "333": "ComfySwitchNode",
    "22": "StringConcatenate",
    "309": "ComfySwitchNode",
    "24": "ComfySwitchNode",
    "332": "StringConcatenate",
    "2": "LoadImage",
    "316": "JWMaskLikeImageSize",
    "324": "easy isMaskEmpty",
    "301": "PrimitiveBoolean",
    "317": "ComfySwitchNode",
    "1": "LoadImage",
    "14": "DapaoOutfitRegions",
    "160": "DapaoHemGuide",
    "13": "easy sam3ImageSegmentation",
    "321": "easy isMaskEmpty",
    "12": "easy sam3ImageSegmentation",
    "315": "easy isMaskEmpty",
    "325": "ComfySwitchNode"
  },
  "prompts": [
    [
      304,
      0,
      "Transfer the full outfit from image 2 onto the person in image 1, head to toe. Inspect the bottom of the reference including underneath the hem. If footwear is visible in the reference and the target feet are in frame, replace BOTH original shoes with that pair. Match visible shoe coverage, toe shape, colors and ornamentation; adapt to the angle of each foot. If no reference shoes are identifiable, leave the original footwear unchanged. Keep the original crop and pose. Edit image 1. Dress the same person in every wearable piece shown together in image 2, including sleeves, drapes, detachable layers and accessories that are actually present. Match their silhouette and construction to the original body and pose, including both shoulders, bare-skin areas between old garments and the spaces around the arms. Keep continuous fabric across the waist when the reference is a dress. Preserve the original face, hair, glasses, hands, phone, pose, framing and background. Respect foreground occlusions. Do not copy a mannequin or its pose. Later images are detail views, not extra garments.",
      "Dress the original person in all visibly present pieces of the main outfit reference. Identify clothing, overlapping layers and identifiable accessories from head to toe, including footwear visible below hems. Match the construction, silhouette and coverage in the person's pose. Apply left and right pieces to the corresponding visible limbs. Preserve identity, hand-held objects, foreground occlusions, framing and background. Keep existing footwear when reference footwear is not identifiable. Do not copy the reference wearer, mannequin or backdrop. Later images refine the main outfit only."
    ],
    [
      318,
      1,
      "If image 2 shows the whole outfit, use only the requested part. For a top from a one-piece garment, transfer its visible bodice, neckline and sleeves to the upper garment of image 1. Keep other garments and the lower body unchanged. If the requested item is genuinely absent, keep the original item.",
      "Apply only the selected items that are visible in the garment reference, together in one edit. Match each item's outline, length, volume, openings and attached parts to that reference. Clothes may cover newly occupied skin or reveal skin and existing layers where the old item extended farther. Respect the wearer's anatomy and foreground occlusions. Keep unselected layers visible outside the new outline, including legwear above footwear and underlayers below hems. Keep framing and background. Do not invent missing items; use later detail views only to refine an identified item."
    ],
    [
      332,
      1,
      "Segmentation could not localize the selected item. Inspect BOTH full images: image 1 is the person, image 2 is the reference. Identify and describe ONLY the requested part from image 2, locate where it belongs on image 1. Preserve original framing, other garments and accessories. If the item is absent, preserve the original appearance.",
      "Automatic localization is incomplete. Locate the requested object on the original person and inspect the supplied garment reference, which may be a focused product view. Keep the surroundings and unrelated garments. If the reference item is not identifiable, preserve the original appearance."
    ]
  ],
  "panel": {
    "full": 301,
    "detailSlots": [
      3,
      4,
      5
    ],
    "fullPrompt": 305,
    "hem1": 160,
    "region1": 14,
    "ai": 23,
    "wide": 334,
    "repair": 339,
    "outfitLora": 32,
    "focus": 343
  }
};
// Apply the known pre-multiselect revision to a serialized canvas. Preserve user
// edits to existing widgets, node positions, inputs and unrelated connections.
export function upgradeOutfitWorkflow(graph, catalog) {
  if (graph?.id !== revision.workflow || !Array.isArray(graph.links)) return false;
  const byId = new Map(graph.nodes.map(n => [n.id, n]));
  const panel = byId.get(10)?.properties;
  if (!panel?.dapaoOutfitPanel) return false;
  const config = typeof panel.dapaoOutfitPanel === "string" ? JSON.parse(panel.dapaoOutfitPanel) : panel.dapaoOutfitPanel;
  if (config.full !== 301 || config.wide || Object.entries(revision.anchors).some(([id,type]) => byId.get(Number(id))?.type !== type)) return false;
  if (!graph.links.every(Array.isArray)) return false;
  // A changed connection belongs to the user. Leave it connected as saved.
  const idMap = new Map();
  let nextNode = Math.max(graph.last_node_id, ...byId.keys(), 350);
  for (const spec of revision.nodes) {
    const n = structuredClone(spec);
    n.id = byId.has(spec.id) ? ++nextNode : spec.id;
    idMap.set(spec.id,n.id);
    byId.set(n.id,n);
    graph.nodes.push(n);
  }
  const resolve = id => idMap.get(id) ?? id;
  let nextLink = Math.max(graph.last_link_id, ...graph.links.map(link => link[0]));
  for (const [from,slot,to,input,prior] of revision.links) {
    const target = byId.get(resolve(to)).inputs[input];
    if (prior) {
      const index = graph.links.findIndex(link => link[0] === target.link && link[1] === prior[0] && link[2] === prior[1]);
      if (index < 0) continue;
      const [old] = graph.links.splice(index,1);
      const output = byId.get(old[1]).outputs[old[2]];
      output.links = output.links.filter(id => id !== old[0]);
    }
    const source = byId.get(resolve(from)).outputs[slot];
    target.link = ++nextLink;
    (source.links ??= []).push(nextLink);
    graph.links.push([nextLink,resolve(from),slot,resolve(to),input,source.type]);
  }
  for (const [id,index,old,text] of revision.prompts) {
    const n = byId.get(id);
    if (n.widgets_values?.[index] !== old) continue;
    n.widgets_values[index] = text;
    const key = n.inputs.filter(i => i.widget)[index]?.name;
    if (key && n.widgets_values_named) n.widgets_values_named[key] = text;
  }
  for (const [key,id] of Object.entries(revision.panel)) if (!(key in config)) config[key] = typeof id === "number" ? resolve(id) : id;
  const items = panel.outfitItems?.length ? panel.outfitItems : [panel.outfitItem || byId.get(10).widgets_values[0]];
  byId.get(config.focus).widgets_values[0] = items.length === 1 && catalog.focusItems.includes(items[0]);
  const hem = byId.get(config.hem1).widgets_values[0];
  byId.get(config.wide).widgets_values[0] = hem === "沿用原轮廓" && (items.length > 1 || !catalog.localDetails.includes(items[0]));
  panel.dapaoOutfitPanel = JSON.stringify(config);
  graph.last_node_id = nextNode;
  graph.last_link_id = nextLink;
  return true;
}
// Upgrade existing canvases in place so masks and user-saved settings survive reloads.
export function upgradeReferenceScope(graph) {
  if (graph?.id !== revision.workflow || !Array.isArray(graph.links) || !graph.links.every(Array.isArray)) return false;
  const nodes=new Map(graph.nodes.map(n=>[n.id,n]));
  const props=nodes.get(10)?.properties;
  if (!props?.dapaoOutfitPanel) return false;
  const cfg=typeof props.dapaoOutfitPanel==="string"?JSON.parse(props.dapaoOutfitPanel):props.dapaoOutfitPanel;
  if (!cfg.repair || cfg.fullReferenceScope) return false;
  const merge=graph.links.find(l=>l[1]===cfg.repair && l[2]===0 && l[4]===1)?.[3];
  const wideGate=graph.links.find(l=>l[1]===cfg.wide && l[2]===0 && l[4]===1)?.[3];
  const prior=(to,input,from)=>graph.links.some(l=>l[3]===to && l[4]===input && l[1]===from);
  if (!cfg.manualScope && (!prior(merge,0,309) || !prior(318,0,10) || !prior(326,1,319) || !prior(wideGate,2,322))) return false;

  let nextNode=Math.max(graph.last_node_id,...nodes.keys());
  let nextLink=Math.max(graph.last_link_id,...graph.links.map(l=>l[0]));
  function node(type,title,inputs,output,values) {
    const id=++nextNode;
    const n={id,type,title,pos:[3650,1500+(id-graph.last_node_id-1)*66],size:[340,135],
      order:0,mode:0,flags:{collapsed:true},properties:{"Node name for S&R":type,"cnr_id":"comfy-core"},
      inputs:inputs.map(([name,t,widget])=>({name,type:t,...(widget?{widget:{name}}:{}),link:null})),
      outputs:[{name:output,type:output,links:[]}],widgets_values:values};
    graph.nodes.push(n);nodes.set(id,n);return id;
  }
  function wire(a,s,b,i) {
    const dst=nodes.get(b).inputs[i];
    if(dst.link!=null){
      const index=graph.links.findIndex(l=>l[0]===dst.link);
      const [old]=graph.links.splice(index,1);
      const output=nodes.get(old[1]).outputs[old[2]];output.links=output.links.filter(x=>x!==old[0]);
    }
    const src=nodes.get(a).outputs[s];dst.link=++nextLink;(src.links??=[]).push(nextLink);
    graph.links.push([nextLink,a,s,b,i,src.type]);
  }
  function choose(title,type,whenFalse,whenTrue,condition){
    const id=node("ComfySwitchNode",title,[["on_false",type],["on_true",type],["switch","BOOLEAN",true]],type,[false]);
    wire(whenFalse,0,id,0);wire(whenTrue,0,id,1);wire(condition,0,id,2);return id;
  }
  function finish(){
    // Full outfit + painted person crops only the person. The reference still
    // supplies the entire outfit (or the explicitly painted products).
    const policy=graph.links.find(l=>l[3]===308 && l[4]===2);
    if(!policy)return false;
    cfg.fullReferenceScope=choose("完整模式保持全套参考","BOOLEAN",policy[1],319,301);
    wire(cfg.fullReferenceScope,0,308,2);props.dapaoOutfitPanel=JSON.stringify(cfg);
    graph.last_node_id=nextNode;graph.last_link_id=nextLink;return true;
  }
  if(cfg.manualScope)return finish();
  const upper=node("StringReplace","上装 · 完整衣身与相连外摆",
    [["string","STRING",true],["find","STRING",true],["replace","STRING",true]],"STRING",
    ["","selected shirt,blouse,sweater from image 2.",
    "ONE complete upper garment from image 2. Follow its outline from shoulder through the waist to its lowest fabric edge. Include attached flounces, layered peplum, overskirt, ribbons and side panels if visible, preserving their spread, tiers and trim as they drape over the original lower garment. A pointed bodice edge is not the end of the garment when a continuous flared panel lies below it. For a straight-hem top use the straight hem. Keep independent bottoms and accessories; uncovered forearms stay as in image 1 unless true attached sleeves extend onto them."]);
  wire(10,2,upper,0);wire(upper,0,318,0);
  const ruleNode=nodes.get(10);
  const extraIndex=ruleNode.inputs.findIndex(input=>input.name==="补充要求");
  const extraInput=ruleNode.inputs[extraIndex];
  const existing=graph.links.find(l=>l[0]===extraInput.link);
  const supplement=node("PrimitiveStringMultiline","按部位补充要求",[["value","STRING",true]],"STRING",[ruleNode.widgets_values?.[3] || ""]);
  if(!existing)wire(supplement,0,10,extraIndex);
  const extra=choose("手绘取件 · 使用当前补充要求","STRING",supplement,305,301);
  if(existing)wire(existing[1],existing[2],extra,0);
  const rule="The user painted a product selection on the garment reference. Image 2 is the isolated selection. Dress the person in EVERY identifiable wearable product shown in this selection, including disconnected pieces. Enumerate each selected item once. Copy the complete silhouette, tier widths and edge trim of a flared or layered hem, any hanging side panels, and every separate accessory inside the selection, including both matching pieces when depicted. Adapt the layering to the original pose: retain visible hem tiers to the sides of crossing hands or thighs. Keep garments, accessories and legwear from image 1 outside what these products cover. Keep face, hands, hair, body proportions, pose, framing and background. A clipped sliver at the boundary is not a new product. Later detail views refine the selected products only.";
  const manual=node("StringConcatenate","服装手绘优先 · 穿上框内单品",[["string_a","STRING",true],["string_b","STRING",true],["delimiter","STRING",true]],"STRING",[rule,"","\n"]);
  wire(extra,0,manual,1);
  const scope=choose("选择手绘取件或按钮取件","STRING",manual,309,324);
  wire(scope,0,merge,0);
  const allowShape=choose("框选多件时保留人物全幅","BOOLEAN",319,cfg.wide,324);
  wire(allowShape,0,wideGate,1);wire(322,0,326,1);
  // Painted inputs are sufficient. Avoid evaluating SAM or category text just
  // to supply an automatic mask that the crop node will discard.
  const refCrop=graph.links.find(l=>l[3]===graph.links.find(x=>x[3]===308 && x[4]===1)?.[1] && l[4]===0)?.[1];
  const refAuto=choose("参考图已手绘时跳过自动取件","MASK",316,317,324);
  wire(refAuto,0,14,3);
  if(nodes.get(refCrop)?.type==="DapaoOutfitRegions")wire(refAuto,0,refCrop,3);
  const auto=graph.links.find(l=>l[3]===160 && l[4]===1);
  const hand=graph.links.find(l=>l[3]===160 && l[4]===2);
  const bodyMask=choose("人物已手绘时跳过自动定位","MASK",hand[1],auto[1],322);
  wire(bodyMask,0,160,1);
  if(!existing)cfg.supplement=supplement;
  cfg.manualScope=scope;return finish();
}
