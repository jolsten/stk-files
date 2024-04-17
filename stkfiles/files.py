import abc
import io
import typing
from typing import List, Optional

import numpy as np

from stkfiles import formatters, validators
from stkfiles.typing import (
    AttitudeFileFormat,
    CentralBody,
    CoordinateAxes,
    DateTime,
    EphemerisFileFormat,
    EulerRotationSequence,
    InterpolationMethod,
    IntervalList,
    MessageLevel,
    RotationSequence,
    TimeFormat,
    YPRRotationSequence,
)

EPOCH_TIME_FORMATS = ["EpSec"]
QUATERNION_FORMATS = ["Quaternions", "QuatScalarFirst"]
ANGLE_FORMATS = ["EulerAngles", "YPRAngles"]
EULER_SEQUENCES = typing.get_args(EulerRotationSequence)
YPR_SEQUENCES = typing.get_args(YPRRotationSequence)
COORD_AXES_REQUIRE_EPOCH = [
    "MeanOfEpoch",
    "TrueOfEpoch",
    "TEMEOfEpoch",
    "AlignmentAtEpoch",
]


def _ensure_shapes_match(*args: np.ndarray) -> None:
    expected_rows = None
    for idx, shape in enumerate([a.shape for a in args]):
        if expected_rows is None:
            expected_rows = shape[0]
        else:
            if shape[0] != expected_rows:
                msg = f"ndarray {idx} with shape {shape} does not match expected row count {expected_rows}"
                raise ValueError(msg)


class StkFileBase(abc.ABC):
    __version__: str = "stk.v.11.0"
    __name__: str = ...

    format: str = ...
    formatter: callable
    validator: callable

    def __init__(
        self,
        stream: io.TextIOBase,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
    ) -> None:
        """Initialize the STK File base class.

        Implements much of the functionality needed for writing STK data files. This implementation allows
        both batched and streaming file writing to be handled by the same class.

        Args:
            stream:
                The stream on which to write the file contents.
                e.g. a file handle or io.StringIO()
            message_level:
                The verbosity level of STK as it relates to reading the file.
                Options are: Errors, Warnings, Verbose
            time_format:
                The format of the times to be used in the file. Options are:
                - ISO-YMD: ISO-8601 DateTime, i.e. YYYY-MM-DDTHH:MM:SS.sss
                - EpSec: Seconds since the scenario epoch
            scenario_epoch:
                The epoch time referenced by the STK file. time_format="EpSec" requires a ScenarioEpoch be provide.

        Returns:
            None

        Raises:
            ValueError: An argument was invalid.
        """
        self.stream = stream

        self.message_level = validators.choice(message_level, MessageLevel)
        self.time_format = validators.choice(time_format, TimeFormat)
        self.scenario_epoch = validators.time(scenario_epoch)

        if self.time_format == "ISO-YMD":
            self.format_time = formatters.iso_ymd
        elif self.time_format == "EpSec":
            self.format_time = formatters.ep_sec
        else:
            msg = f"time_format={self.time_format!r} is not supported"
            raise NotImplementedError(msg)

        # Do more complicated argument validation here
        self._validate_time_format_with_epoch()

    def __enter__(self) -> "StkFileBase":
        self.write_header()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self.write_footer()

    def _validate_time_format_with_epoch(self) -> None:
        """Ensure the ScenarioEpoch keyword is provided only when the TimeFormat requires it."""
        if self.time_format in EPOCH_TIME_FORMATS and not self.scenario_epoch:
            msg = f"time_format={self.time_format!r} requires a scenario_epoch value"
            raise ValueError(msg)

        if self.scenario_epoch and self.time_format not in EPOCH_TIME_FORMATS:
            msg = f"scenario_epoch argument is not applicable for time_format={self.time_format!r}"
            raise ValueError(msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(stream={self.stream})"

    def _make_header(self) -> List[str]:
        """Assemble the STK file header.

        Returns:
            A list of strings containing the necessary file header lines.

            [
                "stk.v.11.0",
                "BEGIN Attitude",
                "<Keyword1> <Value1>",
                ...
                "<KeywordN> <ValueN>",
                "AttitudeTimeQuaternions",
            ]
        """
        hdr = [self.__version__, f"BEGIN {self.__name__}"]
        if self.message_level:
            hdr.append(f"MessageLevel        {self.message_level}")
        if self.time_format:
            hdr.append(f"TimeFormat          {self.time_format}")
        if self.scenario_epoch:
            hdr.append(f"ScenarioEpoch       {self.format_time(self.scenario_epoch)}")
        return hdr

    def _make_footer(self) -> List[str]:
        """Assemble the STK file footer.

        Returns:
            A list of strings containing the necessary file footer lines.

            [
                "END Attitude",
            ]
        """
        return [f"END {self.__name__}"]

    def write_header(self) -> None:
        """Write the header to the stream."""
        for line in self._make_header():
            print(line, file=self.stream)

    def write_batch(self, time: np.ndarray, data: np.ndarray) -> None:
        """Validate, format and write data to the stream.

        Args:
            time:
                A numpy.ndarray[datetime64] containing the times for each row of data.
            data:
                A numpy.ndarray containing the rows of data to write to the STK Data File.

        Returns:
            None
        """
        time = np.atleast_1d(time)
        data = np.atleast_2d(data)
        _ensure_shapes_match(time, data)

        time, data = self.validator(time, data)

        for t, row in zip(time, data):
            print(self.format_time(t), self.formatter(row), file=self.stream)

    def write_footer(self) -> None:
        """Write the footer to the stream."""
        for line in self._make_footer():
            print(line, file=self.stream)

    def write_complete(self, time: np.ndarray, data: np.ndarray) -> None:
        """Write a complete STK Data File given a a complete set of input data.

        Args:
            time:
                A numpy.ndarray[datetime64] containing the times for each row of data.
            data:
                A numpy.ndarray containing the rows of data to write to the STK Data File.

        Returns:
            None
        """
        self.write_header()
        self.write_batch(time, data)
        self.write_footer()

    def _validate_coord_axes_with_epoch(self) -> None:
        """Ensure the CoordinateAxesEpoch keyword is provided when CoordinateAxes requires it.

        Raises:
            ValueError: The CoordinateAxesEpoch is required but was not provided.
        """
        if (
            self.coordinate_axes in COORD_AXES_REQUIRE_EPOCH
            and self.coordinate_axes_epoch is None
        ):
            msg = f"coordinate_axes={self.coordinate_axes!r} requires a coordinate_axes_epoch value"
            raise ValueError(msg)


class AttitudeFile(StkFileBase):
    __name__ = "Attitude"

    def __init__(
        self,
        stream: io.TextIOBase,
        format: AttitudeFileFormat,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
        central_body: Optional[CentralBody] = None,
        coordinate_axes: CoordinateAxes = "ICRF",
        coordinate_axes_epoch: Optional[DateTime] = None,
        interpolation_method: Optional[InterpolationMethod] = None,
        interpolation_order: Optional[int] = None,
        sequence: Optional[RotationSequence] = None,
    ) -> None:
        """Initializes the STK Attitude (.a) File writer.

        Args:
            stream:
                The stream on which to write the file contents.
                e.g. a file handle or io.StringIO()
            format:
                The format of the attitude data being used. Options include:
                - Quaternions
                - QuatScalarFirst
                - EulerAngles
                - YPRAngles
            sequence:
                The rotation sequence for the attitude data.
                Required if format is "EulerAngles" or "YPRAngles".
            message_level:
                The verbosity level of STK as it relates to reading the file.
                Options are: Errors, Warnings, Verbose
            time_format:
                The format of the times to be used in the file. Options are:
                - ISO-YMD: ISO-8601 DateTime, i.e. YYYY-MM-DDTHH:MM:SS.sss
                - EpSec: Seconds since the scenario epoch
            scenario_epoch:
                The epoch time referenced by the STK file. time_format="EpSec" requires a ScenarioEpoch be provide.
            central_body:
                The central body.
            coordinate_axes:
                The coordinate axes for the data. Default is "ICRF". Options include:
                - Fixed: The standard Greenwich-referenced ECF frame.
                - ICRF: The International Celestial Reference Frame
                - J2000: The same as ICRF (maybe?)
                - Inertial
                - TrueOfDate
                - MeanOfDate
                - TEMEOfDate
            coordinate_axes_epoch:
                The epoch (datetime) to use as the epoch for the associated reference frame.
                Required `if coordinate_axes in ["TrueOfDate", "MeanOfDate", "TEMEOfDate"]`
            interpolation_method:
                The interpolation method used by STK. Options are "Lagrange" or "Hermite".
            interpolation_order:
                The order of the interpolation method used.

        Returns:
            None

        Raises:
            ValueError: An argument was invalid.
        """
        super().__init__(
            stream,
            message_level=message_level,
            time_format=time_format,
            scenario_epoch=scenario_epoch,
        )
        self.format = validators.choice(format, AttitudeFileFormat)
        self.central_body = validators.choice(central_body, CentralBody)

        # Don't validate coordinate axes to allow custom systems in the vector geometry tool
        self.coordinate_axes = coordinate_axes

        self.coordinate_axes_epoch = validators.time(coordinate_axes_epoch)
        self.interpolation_method = validators.choice(
            interpolation_method, InterpolationMethod
        )
        self.interpolation_order = validators.integer(interpolation_order)
        self.sequence = validators.choice(sequence, EulerRotationSequence)

        self._validate_coord_axes_with_epoch()
        self._validate_angles_with_sequence()

        self.validator = validators.none

        self.formatter = formatters.generic
        if self.format in QUATERNION_FORMATS:
            self.validator = validators.quaternion
            self.formatter = formatters.quaternions
        elif self.format in ANGLE_FORMATS:
            self.validator = validators.angles

    def _validate_coord_axes_with_epoch(self) -> None:
        """Ensure the CoordinateAxesEpoch keyword is provided when CoordinateAxes requires it.

        Raises:
            ValueError: The CoordinateAxesEpoch is required but was not provided.
        """
        if (
            self.coordinate_axes in COORD_AXES_REQUIRE_EPOCH
            and self.coordinate_axes_epoch is None
        ):
            msg = f"coordinate_axes={self.coordinate_axes!r} requires a coordinate_axes_epoch value"
            raise ValueError(msg)

    def _validate_angles_with_sequence(self) -> None:
        """Ensure the Sequence keyword is provided if format requires it.

        Raises:
            ValueError: The CoordinateAxesEpoch is required but was not provided.
        """
        if self.format in ANGLE_FORMATS:
            if self.sequence is None:
                msg = f"format={self.format} requires a sequence value"
                raise ValueError(msg)

            if self.format == "YPRAngles" and self.sequence not in YPR_SEQUENCES:
                msg = f"sequence={self.sequence} not valid for format={self.format}"
                raise ValueError(msg)

            if self.format == "EulerAngles" and self.sequence not in EULER_SEQUENCES:
                msg = f"sequence={self.sequence} not valid for format={self.format}"
                raise ValueError(msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(stream={self.stream}, format={self.format})"

    def _make_header(self) -> List[str]:
        hdr = []
        hdr.extend(super()._make_header())
        if self.central_body:
            hdr.append(f"CentralBody         {self.central_body}")
        if self.coordinate_axes:
            hdr.append(f"CoordinateAxes      {self.coordinate_axes}")
        if self.coordinate_axes_epoch:
            hdr.append(
                f"CoordinateAxesEpoch {self.format_time(self.coordinate_axes_epoch)}"
            )
        if self.interpolation_method:
            hdr.append(f"InterpolationMethod {self.interpolation_method}")
        if self.interpolation_order:
            hdr.append(f"InterpolationOrder  {self.interpolation_order}")
        if self.sequence:
            hdr.append(f"Sequence {self.sequence}")

        hdr.append(f"AttitudeTime{self.format}")
        return hdr


class SensorPointingFile(AttitudeFile):
    __name__ = "Attitude"

    def __init__(
        self,
        stream: io.TextIOBase,
        format: AttitudeFileFormat,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
        central_body: Optional[CentralBody] = None,
        coordinate_axes: CoordinateAxes = "ICRF",
        coordinate_axes_epoch: Optional[DateTime] = None,
        interpolation_method: Optional[InterpolationMethod] = None,
        interpolation_order: Optional[int] = None,
        sequence: Optional[RotationSequence] = None,
    ) -> None:
        """Initializes the STK Attitude (.a) File writer.

        Args:
            stream:
                The stream on which to write the file contents.
                e.g. a file handle or io.StringIO()
            format:
                The format of the attitude data being used. Options include:
                - Quaternions
                - QuatScalarFirst
                - EulerAngles
                - YPRAngles
            sequence:
                The rotation sequence for the attitude data.
                Required if format is "EulerAngles" or "YPRAngles".
            message_level:
                The verbosity level of STK as it relates to reading the file.
                Options are: Errors, Warnings, Verbose
            time_format:
                The format of the times to be used in the file. Options are:
                - ISO-YMD: ISO-8601 DateTime, i.e. YYYY-MM-DDTHH:MM:SS.sss
                - EpSec: Seconds since the scenario epoch
            scenario_epoch:
                The epoch time referenced by the STK file. time_format="EpSec" requires a ScenarioEpoch be provide.
            central_body:
                The central body.
            coordinate_axes:
                The coordinate axes for the data. Default is "ICRF". Options include:
                - Fixed: The standard Greenwich-referenced ECF frame.
                - ICRF: The International Celestial Reference Frame
                - J2000: The same as ICRF (maybe?)
                - Inertial
                - TrueOfDate
                - MeanOfDate
                - TEMEOfDate
            coordinate_axes_epoch:
                The epoch (datetime) to use as the epoch for the associated reference frame.
                Required `if coordinate_axes in ["TrueOfDate", "MeanOfDate", "TEMEOfDate"]`
            interpolation_method:
                The interpolation method used by STK. Options are "Lagrange" or "Hermite".
            interpolation_order:
                The order of the interpolation method used.

        Returns:
            None

        Raises:
            ValueError: An argument was invalid.
        """
        super().__init__(
            stream,
            message_level=message_level,
            time_format=time_format,
            scenario_epoch=scenario_epoch,
        )
        self.format = validators.choice(format, AttitudeFileFormat)
        self.central_body = validators.choice(central_body, CentralBody)

        # Don't validate coordinate axes to allow custom systems in the vector geometry tool
        self.coordinate_axes = coordinate_axes

        self.coordinate_axes_epoch = validators.time(coordinate_axes_epoch)
        self.interpolation_method = validators.choice(
            interpolation_method, InterpolationMethod
        )
        self.interpolation_order = validators.integer(interpolation_order)
        self.sequence = validators.choice(sequence, EulerRotationSequence)

        self._validate_coord_axes_with_epoch()
        self._validate_angles_with_sequence()

        self.validator = validators.none

        self.formatter = formatters.generic
        if self.format in QUATERNION_FORMATS:
            self.validator = validators.quaternion
            self.formatter = formatters.quaternions
        elif self.format in ANGLE_FORMATS:
            self.validator = validators.angles

    def _validate_coord_axes_with_epoch(self) -> None:
        """Ensure the CoordinateAxesEpoch keyword is provided when CoordinateAxes requires it.

        Raises:
            ValueError: The CoordinateAxesEpoch is required but was not provided.
        """
        if (
            self.coordinate_axes in COORD_AXES_REQUIRE_EPOCH
            and self.coordinate_axes_epoch is None
        ):
            msg = f"coordinate_axes={self.coordinate_axes!r} requires a coordinate_axes_epoch value"
            raise ValueError(msg)

    def _validate_angles_with_sequence(self) -> None:
        """Ensure the Sequence keyword is provided if format requires it.

        Raises:
            ValueError: The CoordinateAxesEpoch is required but was not provided.
        """
        if self.format in ANGLE_FORMATS:
            if self.sequence is None:
                msg = f"format={self.format} requires a sequence value"
                raise ValueError(msg)

            if self.format == "YPRAngles" and self.sequence not in YPR_SEQUENCES:
                msg = f"sequence={self.sequence} not valid for format={self.format}"
                raise ValueError(msg)

            if self.format == "EulerAngles" and self.sequence not in EULER_SEQUENCES:
                msg = f"sequence={self.sequence} not valid for format={self.format}"
                raise ValueError(msg)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(stream={self.stream}, format={self.format})"

    def _make_header(self) -> List[str]:
        hdr = []
        hdr.extend(super()._make_header())
        if self.central_body:
            hdr.append(f"CentralBody         {self.central_body}")
        if self.coordinate_axes:
            hdr.append(f"CoordinateAxes      {self.coordinate_axes}")
        if self.coordinate_axes_epoch:
            hdr.append(
                f"CoordinateAxesEpoch {self.format_time(self.coordinate_axes_epoch)}"
            )
        if self.interpolation_method:
            hdr.append(f"InterpolationMethod {self.interpolation_method}")
        if self.interpolation_order:
            hdr.append(f"InterpolationOrder  {self.interpolation_order}")
        if self.sequence:
            hdr.append(f"Sequence {self.sequence}")

        hdr.append(f"AttitudeTime{self.format}")
        return hdr


class EphemerisFile(StkFileBase):
    __version__: str = "stk.v.12.0"
    __name__: str = "Ephemeris"

    def __init__(
        self,
        stream: io.TextIOBase,
        format: EphemerisFileFormat,
        *,
        message_level: Optional[MessageLevel] = None,
        time_format: Optional[TimeFormat] = "ISO-YMD",
        scenario_epoch: Optional[DateTime] = None,
        central_body: Optional[CentralBody] = None,
        coordinate_axes: CoordinateAxes = "ICRF",
        coordinate_axes_epoch: Optional[DateTime] = None,
        interpolation_method: Optional[InterpolationMethod] = None,
        interpolation_order: Optional[int] = None,
    ) -> None:
        """Initializes the STK Ephemeris (.e) File writer.

        Args:
            stream:
                The stream on which to write the file contents.
                e.g. a file handle or io.StringIO()
            format:
                The format of the attitude data being used. Options include:
                - TimePos
                - TimePosVel
                - LLATimePos
                - LLATimePosVel
            message_level:
                The verbosity level of STK as it relates to reading the file.
                Options are: Errors, Warnings, Verbose
            time_format:
                The format of the times to be used in the file. Options are:
                - ISO-YMD: ISO-8601 DateTime, i.e. YYYY-MM-DDTHH:MM:SS.sss
                - EpSec: Seconds since the scenario epoch
            scenario_epoch:
                The epoch time referenced by the STK file. time_format="EpSec" requires a ScenarioEpoch be provide.
            central_body:
                The central body.
            coordinate_axes:
                The coordinate axes for the data. Default is "ICRF". Options include:
                - Fixed: The standard Greenwich-referenced ECF frame.
                - ICRF: The International Celestial Reference Frame
                - J2000: The same as ICRF (maybe?)
                - Inertial
                - TrueOfDate
                - MeanOfDate
                - TEMEOfDate
            coordinate_axes_epoch:
                The epoch (datetime) to use as the epoch for the associated reference frame.
                Required `if coordinate_axes in ["TrueOfDate", "MeanOfDate", "TEMEOfDate"]`
            interpolation_method:
                The interpolation method used by STK. Options are "Lagrange" or "Hermite".
            interpolation_order:
                The order of the interpolation method used.

        Returns:
            None

        Raises:
            ValueError: An argument was invalid.
        """
        super().__init__(
            stream,
            message_level=message_level,
            time_format=time_format,
            scenario_epoch=scenario_epoch,
        )
        self.format = validators.choice(format, EphemerisFileFormat)
        self.central_body = validators.choice(central_body, CentralBody)
        self.coordinate_axes = validators.choice(coordinate_axes, CoordinateAxes)
        self.coordinate_axes_epoch = validators.time(coordinate_axes_epoch)
        self.interpolation_method = validators.choice(
            interpolation_method, InterpolationMethod
        )
        self.interpolation_order = validators.integer(interpolation_order)

        self._validate_coord_axes_with_epoch()

        self.validator = validators.none
        self.formatter = formatters.generic


class IntervalFile(StkFileBase):
    __version__: str = "stk.v.10.0"
    __name__: str = "IntervalList"

    def __init__(
        self,
        stream: io.TextIOBase,
        *,
        message_level: Optional[MessageLevel] = None,
        scenario_epoch: Optional[DateTime] = None,
    ) -> None:
        """Initializes the STK Interval (.int) File writer.

        Args:
            stream:
            message_level:
            scenario_epoch:

        """
        super().__init__(
            stream,
            message_level=message_level,
            scenario_epoch=scenario_epoch,
        )

        self.validator = validators.none

    def _make_header(self) -> List[str]:
        # hdr = super()._make_header()
        hdr = ["stk.v.12.0"]
        hdr.append("BEGIN IntervalList")
        hdr.append("    DateUnitAbrv ISO-YMD")
        hdr.append("BEGIN Intervals")
        return hdr

    def _make_footer(self) -> List[str]:
        ftr = []
        ftr.append("END Intervals")
        ftr.append("END IntervalList")
        return ftr

    def write_batch(
        self,
        intervals: IntervalList,
    ) -> List[str]:
        """Validate, format and write data to the stream.

        Args:
            intervals: An iterable containing start, stop time pairs with optionally additional elements for "data"

        Returns:
            None
        """
        for parts in intervals:
            t0, t1, *data = parts
            t0 = formatters.iso_ymd(t0)
            t1 = formatters.iso_ymd(t1)
            print(f'"{t0}"', f'"{t1}"', *data, file=self.stream)

    def write_complete(
        self,
        intervals: IntervalList,
    ) -> None:
        """Write a complete STK Data File given a a complete set of input data.

        Args:
            intervals: An iterable containing start, stop time pairs with optionally additional elements for "data"

        Returns:
            None
        """
        self.write_header()
        self.write_batch(intervals)
        self.write_footer()
