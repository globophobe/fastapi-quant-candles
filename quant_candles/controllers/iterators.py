from datetime import datetime
from typing import Generator, List, Tuple

from django.conf import settings
from django.db import models
from django.db.models import Q

from quant_candles.lib import (
    get_current_time,
    get_existing,
    get_min_time,
    has_timestamps,
    iter_missing,
    iter_timeframe,
)
from quant_candles.models import (
    Candle,
    CandleCache,
    CandleData,
    CandleReadOnlyData,
    Symbol,
    TradeData,
)


def aggregate_candles(
    candle: Candle,
    timestamp_from: datetime,
    timestamp_to: datetime,
    step: str = "1d",
    retry: bool = False,
) -> None:
    """Aggregate candles."""
    initial = candle.initialize(timestamp_from, timestamp_to, step, retry)
    min_timestamp_from, max_timestamp_to, cache_data, cache_data_frame = initial
    for ts_from, ts_to in CandleCacheIterator(candle).iter_all(
        min_timestamp_from, max_timestamp_to, step, retry=retry
    ):
        data_frame = candle.get_data_frame(ts_from, ts_to)
        cache_data, cache_data_frame = candle.get_cache(
            ts_from, cache_data, cache_data_frame
        )
        data, cache_data, cache_data_frame = candle.aggregate(
            ts_from, ts_to, data_frame, cache_data, cache_data_frame
        )
        candle.write_cache(ts_from, ts_to, cache_data, cache_data_frame)
        candle.write_data(ts_from, ts_to, data)


class BaseTimeFrameIterator:
    def __init__(self, obj: models.Model) -> None:
        self.obj = obj
        self.reverse = None

    def get_max_timestamp_to(self) -> datetime:
        """Get max timestamp to."""
        return get_min_time(get_current_time(), value="1t")

    def iter_all(
        self,
        timestamp_from: datetime,
        timestamp_to: datetime,
        step: str = "1d",
        retry: bool = False,
    ) -> Generator[Tuple[datetime, datetime], None, None]:
        """Iter all, default by days in 1 hour chunks, further chunked by 1m intervals.

        1 day -> 24 hours -> 60 minutes or 10 minutes, etc.
        """
        for ts_from, ts_to, existing in self.iter_range(
            timestamp_from, timestamp_to, step, retry=retry
        ):
            for hourly_timestamp_from, hourly_timestamp_to in self.iter_hours(
                ts_from, ts_to, existing
            ):
                yield hourly_timestamp_from, hourly_timestamp_to

    def iter_range(
        self,
        timestamp_from: datetime,
        timestamp_to: datetime,
        step: str = "1d",
        retry: bool = False,
    ):
        """Iter range."""
        for ts_from, ts_to in iter_timeframe(
            timestamp_from, timestamp_to, step, reverse=self.reverse
        ):
            existing = self.get_existing(ts_from, ts_to, retry=retry)
            if not has_timestamps(ts_from, ts_to, existing):
                if self.can_iter(ts_from, ts_to):
                    yield ts_from, ts_to, existing

    def can_iter(self, timestamp_from: datetime, timestamp_to: datetime) -> bool:
        """Can iter."""
        return True

    def iter_hours(
        self,
        timestamp_from: datetime,
        timestamp_to: datetime,
        partition_existing: List[datetime],
    ):
        """Iter hours."""
        for ts_from, ts_to in iter_timeframe(
            timestamp_from, timestamp_to, value="1h", reverse=self.reverse
        ):
            # List comprehension for hourly.
            existing = [
                timestamp
                for timestamp in partition_existing
                if timestamp >= ts_from and timestamp < ts_to
            ]
            if not has_timestamps(ts_from, ts_to, existing):
                for start_time, end_time in iter_missing(
                    ts_from, ts_to, existing, reverse=self.reverse
                ):
                    max_timestamp_to = self.get_max_timestamp_to()
                    end = max_timestamp_to if end_time > max_timestamp_to else end_time
                    if start_time != end:
                        yield start_time, end_time


class TradeDataIterator(BaseTimeFrameIterator):
    def __init__(self, symbol: Symbol) -> None:
        self.symbol = symbol
        # Trade data iterates from present to past.
        self.reverse = True

    def get_existing(
        self, timestamp_from: datetime, timestamp_to: datetime, retry: bool = False
    ) -> List[datetime]:
        """Get existing."""
        queryset = TradeData.objects.filter(
            symbol=self.symbol,
            timestamp__gte=timestamp_from,
            timestamp__lt=timestamp_to,
        )
        if retry:
            queryset = queryset.exclude(ok=False)
        return get_existing(queryset.values("timestamp", "frequency"))


class CandleCacheIterator(BaseTimeFrameIterator):
    def __init__(self, candle: Candle) -> None:
        self.candle = candle
        # Candle data iterates from past to present.
        self.reverse = False

    def get_existing(
        self, timestamp_from: datetime, timestamp_to: datetime, retry: bool = False
    ) -> List[datetime]:
        """Get existing.

        Retry only locally, as the SQLite database not modifiable in Docker image.
        """
        query = Q(timestamp__gte=timestamp_from) & Q(timestamp__lt=timestamp_to)
        candle_cache = CandleCache.objects.filter(Q(candle=self.candle) & query)
        if settings.IS_LOCAL and retry:
            candle_data = CandleData.objects.filter(Q(candle=self.candle) & query)
            candle_read_only_data = CandleReadOnlyData.objects.filter(
                Q(candle_id=self.candle.id) & query
            )
            for queryset in (candle_cache, candle_data, candle_read_only_data):
                queryset.delete()
            return []
        else:
            return get_existing(candle_cache.values("timestamp", "frequency"))

    def can_iter(self, timestamp_from: datetime, timestamp_to: datetime) -> bool:
        """Can iter."""
        return self.candle.can_aggregate(timestamp_from, timestamp_to)
