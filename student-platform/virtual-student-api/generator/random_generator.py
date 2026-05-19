import random
from datetime import datetime

from .base import GeneratorParams


class RandomGenerator:
    """균등 분포 기반 랜덤 생성기.

    - categorical: value_options 중 균등 랜덤 선택
    - numeric:     value_range 내 균등 분포 (uniform)
    - text:        default_value 사용
    """

    def generate(self, params: GeneratorParams, feature_definitions: list) -> list[dict]:
        ts = datetime.utcnow().strftime("%m%d%H%M")
        students = []
        for i in range(params.count):
            fvs = {fd.key: self._sample(fd) for fd in feature_definitions}
            name = self._make_name(fvs, i + 1, ts)
            students.append({
                "name": name,
                "description": f"자동 생성 가상 학생 ({ts}-{i+1:03d})",
                "subject_id": params.subject_id,
                "feature_values": fvs,
            })
        return students

    def _sample(self, fd) -> str:
        if fd.value_type == "categorical" and fd.value_options:
            return random.choice(fd.value_options)
        if fd.value_type == "numeric":
            r = fd.value_range or {}
            lo, hi = float(r.get("min", 0)), float(r.get("max", 1))
            return str(round(random.uniform(lo, hi), 2))
        return fd.default_value or ""

    def _make_name(self, fvs: dict, index: int, ts: str) -> str:
        depth = fvs.get("conceptual_depth", "")
        style = fvs.get("reasoning_style", "")
        label = f"{depth}_{style}" if depth and style else f"학습자"
        return f"{label}_{ts}_{index:03d}"
