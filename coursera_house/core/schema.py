from marshmallow import Schema, fields
from marshmallow.validate import Range


class ControllerSchema(Schema):
    bedroom_target_temperature = fields.Int(validate=Range(5, 80), strict=True)
    hot_water_target_temperature = fields.Int(validate=Range(5, 80), strict=True)
    bedroom_light = fields.Bool()
    bathroom_light = fields.Bool()
