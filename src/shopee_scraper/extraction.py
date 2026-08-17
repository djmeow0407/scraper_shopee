"""Theo dõi selector: mỗi field ghi khớp primary/fallback/miss. Field trượt sạch
hoặc sống nhờ fallback là dấu hiệu Shopee đổi DOM, đỡ phải đoán khi kết quả rỗng."""

from __future__ import annotations

from dataclasses import dataclass

PRIMARY = "primary"
FALLBACK = "fallback"
MISS = "miss"

# Ngưỡng gắn cờ.
_DEAD_MIN = 3  # cần ít nhất ngần này lượt bóc mới dám kết luận
_DEGRADED_RATE = 0.5


@dataclass
class FieldStat:
    total: int = 0
    primary: int = 0
    fallback: int = 0
    miss: int = 0

    def observe(self, tier: str) -> None:
        self.total += 1
        setattr(self, tier, getattr(self, tier) + 1)

    @property
    def hit(self) -> int:
        return self.primary + self.fallback

    @property
    def miss_rate(self) -> float:
        return self.miss / self.total if self.total else 0.0

    @property
    def fallback_rate(self) -> float:
        return self.fallback / self.hit if self.hit else 0.0


class ExtractionReport:
    def __init__(self) -> None:
        self.fields: dict[str, FieldStat] = {}

    def record(self, field: str, tier: str) -> None:
        self.fields.setdefault(field, FieldStat()).observe(tier)

    def flags(self) -> list[str]:
        """Cảnh báo cần người xem, một dòng mỗi field khả nghi."""
        out = []
        for name, stat in sorted(self.fields.items()):
            if stat.total < _DEAD_MIN:
                continue
            if stat.miss == stat.total:
                out.append(f"selector-dead: {name} (0/{stat.total} lần khớp)")
            elif stat.fallback_rate >= _DEGRADED_RATE:
                out.append(
                    f"selector-degraded: {name} "
                    f"(primary hỏng, {stat.fallback}/{stat.hit} lượt phải dùng fallback)"
                )
        return out

    def to_dict(self) -> dict:
        return {
            name: {
                "total": s.total,
                "primary": s.primary,
                "fallback": s.fallback,
                "miss": s.miss,
            }
            for name, s in sorted(self.fields.items())
        }
