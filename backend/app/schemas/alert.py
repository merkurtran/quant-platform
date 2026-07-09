from typing import Literal, Union, Annotated
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class PriceAboveCondition(BaseModel):
    rule_type: Literal["price_above"]
    value: Decimal = Field(gt=0)
    model_config = {"extra": "forbid"}


class PriceBelowCondition(BaseModel):
    rule_type: Literal["price_below"]
    value: Decimal = Field(gt=0)
    model_config = {"extra": "forbid"}


class PctChangeCondition(BaseModel):
    rule_type: Literal["pct_change"]
    operator: Literal["gt", "lt"]
    value: Decimal = Field(gt=0, le=1000)
    baseline: Literal["previous_close", "rule_created_price", "custom"] = "previous_close"
    custom_baseline: Decimal | None = Field(default=None, gt=0)  # 仅 baseline="custom" 时必填
    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_custom_baseline(self) -> "PctChangeCondition":
        """跨字段校验: baseline=custom 时 custom_baseline 必填"""
        if self.baseline == "custom" and self.custom_baseline is None:
            raise ValueError("custom_baseline is required when baseline='custom'")
        if self.baseline != "custom" and self.custom_baseline is not None:
            raise ValueError("custom_baseline should only be set when baseline='custom'")
        return self


class VolumeSpikeCondition(BaseModel):
    """TODO: 本期先用宽松结构,具体触发规则(比如相对N日均量的倍数)以后细化"""
    rule_type: Literal["volume_spike"]
    params: dict = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class IndicatorCondition(BaseModel):
    """TODO: 本期先用宽松结构,具体指标类型(MACD/RSI等)和参数以后细化"""
    rule_type: Literal["indicator"]
    params: dict = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


AlertConditionUnion = Annotated[
    Union[
        PriceAboveCondition,
        PriceBelowCondition,
        PctChangeCondition,
        VolumeSpikeCondition,
        IndicatorCondition,
    ],
    Field(discriminator="rule_type"),
]


class CreateAlertRuleRequest(BaseModel):
    symbol: str
    condition: AlertConditionUnion
    notify_channels: list[str] = ["inapp"]


class UpdateAlertRuleRequest(BaseModel):
    """只允许改condition和status,不允许改symbol/rule_type——换股票或换类型应该是删了重建,不是"改" """
    condition: AlertConditionUnion | None = None
    status: Literal["active", "paused"] | None = None


class AlertRulePublic(BaseModel):
    id: int
    symbol: str
    rule_type: str
    condition: dict
    notify_channels: list[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertLogPublic(BaseModel):
    id: int
    triggered_at: datetime
    trigger_value: Decimal | None
    message: str | None

    model_config = {"from_attributes": True}