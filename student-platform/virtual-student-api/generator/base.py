from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class GeneratorParams:
    """가상 학생 생성 파라미터.

    count 외 파라미터(분포 설정, 시드, 전략 등)는 향후 이 클래스를 확장한다.
    라우터→generator 경계는 이 dataclass를 통해서만 통신한다.
    """
    subject_id: str
    count: int
    # 향후 확장 예시 (현재 미사용):
    # strategy: str = "random"
    # seed: Optional[int] = None
    # distribution_config: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


@runtime_checkable
class StudentGenerator(Protocol):
    """가상 학생 생성기 인터페이스.

    새 전략을 추가할 때 이 Protocol을 구현하고 factory.py에 등록한다.
    반환값은 VirtualStudent 생성에 필요한 dict 목록:
      [{ name, subject_id, feature_values: {key: value} }, ...]
    """

    def generate(
        self,
        params: GeneratorParams,
        feature_definitions: list,
    ) -> list[dict]:
        ...
