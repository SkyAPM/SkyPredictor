from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TimeBucketStep(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HOUR: _ClassVar[TimeBucketStep]
HOUR: TimeBucketStep

class AlarmBaselineMetricsNames(_message.Message):
    __slots__ = ("metricNames",)
    METRICNAMES_FIELD_NUMBER: _ClassVar[int]
    metricNames: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, metricNames: _Optional[_Iterable[str]] = ...) -> None: ...

class AlarmBaselineRequest(_message.Message):
    __slots__ = ("serviceMetricNames", "startTimeBucket", "endTimeBucket", "step")
    SERVICEMETRICNAMES_FIELD_NUMBER: _ClassVar[int]
    STARTTIMEBUCKET_FIELD_NUMBER: _ClassVar[int]
    ENDTIMEBUCKET_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    serviceMetricNames: _containers.RepeatedCompositeFieldContainer[AlarmBaselineServiceMetricName]
    startTimeBucket: int
    endTimeBucket: int
    step: TimeBucketStep
    def __init__(self, serviceMetricNames: _Optional[_Iterable[_Union[AlarmBaselineServiceMetricName, _Mapping]]] = ..., startTimeBucket: _Optional[int] = ..., endTimeBucket: _Optional[int] = ..., step: _Optional[_Union[TimeBucketStep, str]] = ...) -> None: ...

class AlarmBaselineServiceMetricName(_message.Message):
    __slots__ = ("serviceName", "metricNames")
    SERVICENAME_FIELD_NUMBER: _ClassVar[int]
    METRICNAMES_FIELD_NUMBER: _ClassVar[int]
    serviceName: str
    metricNames: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, serviceName: _Optional[str] = ..., metricNames: _Optional[_Iterable[str]] = ...) -> None: ...

class AlarmBaselineResponse(_message.Message):
    __slots__ = ("serviceMetrics",)
    SERVICEMETRICS_FIELD_NUMBER: _ClassVar[int]
    serviceMetrics: _containers.RepeatedCompositeFieldContainer[AlarmBaselineServiceMetric]
    def __init__(self, serviceMetrics: _Optional[_Iterable[_Union[AlarmBaselineServiceMetric, _Mapping]]] = ...) -> None: ...

class AlarmBaselineServiceMetric(_message.Message):
    __slots__ = ("serviceName", "predictions")
    SERVICENAME_FIELD_NUMBER: _ClassVar[int]
    PREDICTIONS_FIELD_NUMBER: _ClassVar[int]
    serviceName: str
    predictions: _containers.RepeatedCompositeFieldContainer[AlarmBaselineMetricPrediction]
    def __init__(self, serviceName: _Optional[str] = ..., predictions: _Optional[_Iterable[_Union[AlarmBaselineMetricPrediction, _Mapping]]] = ...) -> None: ...

class AlarmBaselineMetricPrediction(_message.Message):
    __slots__ = ("name", "values")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    name: str
    values: _containers.RepeatedCompositeFieldContainer[AlarmBaselinePredicatedValue]
    def __init__(self, name: _Optional[str] = ..., values: _Optional[_Iterable[_Union[AlarmBaselinePredicatedValue, _Mapping]]] = ...) -> None: ...

class AlarmBaselinePredicatedValue(_message.Message):
    __slots__ = ("timeBucket", "singleValue", "labeledValue")
    TIMEBUCKET_FIELD_NUMBER: _ClassVar[int]
    SINGLEVALUE_FIELD_NUMBER: _ClassVar[int]
    LABELEDVALUE_FIELD_NUMBER: _ClassVar[int]
    timeBucket: int
    singleValue: AlarmBaselineSingleValue
    labeledValue: AlarmBaselineLabeledValue
    def __init__(self, timeBucket: _Optional[int] = ..., singleValue: _Optional[_Union[AlarmBaselineSingleValue, _Mapping]] = ..., labeledValue: _Optional[_Union[AlarmBaselineLabeledValue, _Mapping]] = ...) -> None: ...

class AlarmBaselineValue(_message.Message):
    __slots__ = ("value", "upperValue", "lowerValue")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    UPPERVALUE_FIELD_NUMBER: _ClassVar[int]
    LOWERVALUE_FIELD_NUMBER: _ClassVar[int]
    value: int
    upperValue: int
    lowerValue: int
    def __init__(self, value: _Optional[int] = ..., upperValue: _Optional[int] = ..., lowerValue: _Optional[int] = ...) -> None: ...

class AlarmBaselineSingleValue(_message.Message):
    __slots__ = ("value",)
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: AlarmBaselineValue
    def __init__(self, value: _Optional[_Union[AlarmBaselineValue, _Mapping]] = ...) -> None: ...

class AlarmBaselineLabeledValue(_message.Message):
    __slots__ = ("values",)
    class LabelWithValue(_message.Message):
        __slots__ = ("labels", "value")
        LABELS_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        labels: _containers.RepeatedCompositeFieldContainer[KeyStringValuePair]
        value: AlarmBaselineValue
        def __init__(self, labels: _Optional[_Iterable[_Union[KeyStringValuePair, _Mapping]]] = ..., value: _Optional[_Union[AlarmBaselineValue, _Mapping]] = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[AlarmBaselineLabeledValue.LabelWithValue]
    def __init__(self, values: _Optional[_Iterable[_Union[AlarmBaselineLabeledValue.LabelWithValue, _Mapping]]] = ...) -> None: ...

class KeyStringValuePair(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
