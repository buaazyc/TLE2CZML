#!/usr/bin/python
# -*- coding:utf8 -*-

"""
本脚本根据TLE文件生成每颗卫星的CMZL文件，用于前端js使用Cesium显示卫星轨道
"""


# sgp4算法根据二行星历计算每个时间点卫星的位置
from sgp4.earth_gravity import wgs84
from sgp4.io import twoline2rv
import datetime
import json


# 按行读取北斗两行星历文件
# 每三行标识一个卫星，格式如下：
#   BEIDOU 3 (C01)
#   1 36287U 10001A   19315.85946545 -.00000270  00000-0  00000-0 0  9993
#   2 36287   1.3683   8.9730 0004122 163.0332 328.1522  1.00276198 36021
# 星历下载地址：http://celestrak.com/
with open('北斗TLE.txt', 'r') as f:
    data_lines = f.read().split('\n')
assert len(data_lines) % 3 == 0, "TLE每颗卫星数据必须三行:第一行名称，后两行数据"

# 使用字典的数组(json文件)保存每颗卫星的轨道六根数
orbit_info = {}

# 每三行一组，遍历所有卫星
for j in range(len(data_lines) // 3):
    # 第一行名字，后两行数据
    # 数据详细说明：http://celestrak.com/columns/v04n03/
    name = data_lines[j * 3].strip()
    line1 = data_lines[1 + j * 3]
    line2 = data_lines[2 + j * 3]

    # 写轨道六根数到json文件
    # print("卫星轨道倾斜角", line2[8:16], "度")
    # print("升交点赤经", line2[17:25], "度")
    # print("偏心率", line2[26:33])
    # print("近地点角距", line2[34: 42], "度")
    # print("平近点角", line2[43:51], "度")
    # print("平均运动（每天绕地球圈数）", line2[52:63])
    orbit_info.update({
        name: {
            'Inclination': line2[8:16],
            'Right Ascension of the Ascending Node'.replace(' ', '_'): line2[17:25],
            'Eccentricity': line2[26:33],
            'Argument of Perigee'.replace(' ', '_'): line2[34: 42],
            'Mean Anomaly'.replace(' ', '_'): line2[43:51],
            'Mean Motion'.replace(' ', '_'): line2[52:63]
        }
    })

    # 卫星每转1°所经历的时间（单位：秒）
    gap = 1. / float(line2[52:63]) * 24 * 60 * 60 / 360

    # 调用sgp4算法计算星历每个时刻的位置
    satellite = twoline2rv(line1, line2, wgs84)
    assert satellite.error == 0

    # 记录当前时间，并在循环中计算出一个周期后的时间
    # 用于在CZML文件中指定interval
    now_time = datetime.datetime.now()
    next_time = datetime.datetime.now()

    # 保存每1°变化后卫星的位置(x, y, z)：表示具体地心的距离(单位：km)
    position_list = []

    # 循环一圈
    # 每次间隔gap秒
    nums = 361
    for i in range(nums):
        # next_time表示每个位置对应的时间点
        next_time = now_time + datetime.timedelta(seconds=gap * (i + 1))
        # 表示为字典，方便propagate函数的计算
        next_time_str = next_time.strftime('%Y %m %d %H %M %S').split(' ')
        next_time_str = [int(v) for v in next_time_str]
        time_key = ['year', 'month', 'day', 'hour', 'minute', 'second']
        time_map = dict(zip(time_key, next_time_str))

        # 调用sgp4库的propagate函数计算对应时刻的位置
        position, velocity = satellite.propagate(
            year=time_map['year'],
            month=time_map['month'],
            day=time_map['day'],
            hour=time_map['hour'],
            minute=time_map['minute'],
            second=time_map['second']
        )
        # The position vector measures the satellite position in kilometers from the center of the earth.
        # CZML文件中position的格式为：(time, x, y, z, time, x, y, z...)
        position_list.append(next_time.isoformat())
        position_list.append(position[0] * 1000)
        position_list.append(position[1] * 1000)
        position_list.append(position[2] * 1000)

    # 格式化为ISO时间标准格式
    begin = str(now_time.isoformat())
    end = str((next_time + datetime.timedelta(seconds=gap)).isoformat())

    # Write the CZML document to a file
    filename = "F:/中国之星/data/created_by_python/{}.czml".format(name)

    # 初始化CZML
    # CZML实际上是JSON文件，JSON文件就是字典数组
    # 所以使用字典数据结构表示每个卫星
    doc = []

    # 定义头部
    header = {
        # id和version为固定格式
        'id': "document",
        "version": "1.0",
        'name': name,
        "clock": {
            # interval为有效时间，currentTime表示起始点，multiplier表示时钟速度
            "interval": '{}/{}'.format(begin, end),
            "currentTime": begin,
            "multiplier": gap
        }
    }
    doc.append(header)

    # 定义主体
    body = {
        "id": "satellites/{}".format(name),
        "availability": '{}/{}'.format(begin, end),
        "label": {
            # 使用label显示卫星名字
            "font": "11pt Lucida Console",
            "outlineWidth": 2,
            "outlineColor": {"rgba": [0, 0, 0, 255]},
            "horizontalOrigin": "LEFT",
            "pixelOffset": {"cartesian2": [12, 0]},
            "fillColor": {"rgba": [213, 255, 0, 255]},
            "text": name
        },
        "path": {
            # path定义轨道的样式
            "material": {
                "polyline": {
                    "color": {
                        "rgba": [255, 0, 255, 255]
                    }
                }
            },
            "width": 1,
            "resolution": 120
        },
        "billboard": {
            # 卫星的图标，使用base64编码表示图片
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADJSURBVDhPnZHRDcMgEEMZjVEYpaNklIzSEfLfD4qNnXAJSFWfhO7w2Zc0Tf9QG2rXrEzSUeZLOGm47WoH95x3Hl3jEgilvDgsOQUTqsNl68ezEwn1vae6lceSEEYvvWNT/Rxc4CXQNGadho1NXoJ+9iaqc2xi2xbt23PJCDIB6TQjOC6Bho/sDy3fBQT8PrVhibU7yBFcEPaRxOoeTwbwByCOYf9VGp1BYI1BA+EeHhmfzKbBoJEQwn1yzUZtyspIQUha85MpkNIXB7GizqDEECsAAAAASUVORK5CYII=",
            "scale": 1.5
        },
        "position": {
            # cartesian的格式：(time, x, y, z, time, x, y, z...)
            "referenceFrame": "FIXED",  # 可以取FIXED和INERTIAL表示固定和惯性参考系
            # 插值填补轨道
            "interpolationDegree": 5,
            "interpolationAlgorithm": "LAGRANGE",
            "epoch": begin,
            "cartesian": position_list
        }
    }

    # 在body中添加position
    doc.append(body)

    # 使用JSON写CZML文件
    with open(filename, 'w') as f:
        json.dump(doc, f)

# 使用json写轨道信息JSON文件
with open('F:/中国之星/data/orbit_info.json', 'w') as f:
    json.dump(orbit_info, f)
