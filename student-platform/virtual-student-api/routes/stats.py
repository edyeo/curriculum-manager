from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import VirtualStudent, VirtualStudentFeatureDefinition, VirtualStudentFeatureValue
from schemas import (
    StatsResponse,
    FeatureDistribution,
    CategoryDistributionItem,
    NumericDistribution,
    NumericBucket,
)

router = APIRouter(prefix="/api/virtual-students/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def get_stats(subject_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(VirtualStudent)
    if subject_id:
        q = q.filter(VirtualStudent.subject_id == subject_id)
    student_ids = [s.id for s in q.all()]
    total = len(student_ids)

    all_defs = db.query(VirtualStudentFeatureDefinition).all()
    distributions: List[FeatureDistribution] = []

    for fd in all_defs:
        if fd.value_type == "text":
            continue

        fv_query = db.query(VirtualStudentFeatureValue.value).filter(
            VirtualStudentFeatureValue.feature_key == fd.key
        )
        if student_ids:
            fv_query = fv_query.filter(
                VirtualStudentFeatureValue.virtual_student_id.in_(student_ids)
            )
        values = [row[0] for row in fv_query.all()]

        if not values:
            continue

        if fd.value_type == "categorical":
            counts: dict = {}
            for v in values:
                counts[v] = counts.get(v, 0) + 1
            total_vals = len(values)
            order = fd.value_options or []
            dist = [
                CategoryDistributionItem(
                    value=k,
                    count=v,
                    ratio=round(v / total_vals, 2),
                )
                for k, v in sorted(
                    counts.items(),
                    key=lambda x: order.index(x[0]) if x[0] in order else 999,
                )
            ]

        else:  # numeric
            floats = []
            for v in values:
                try:
                    floats.append(float(v))
                except (ValueError, TypeError):
                    pass
            if not floats:
                continue
            min_v = min(floats)
            max_v = max(floats)
            mean_v = sum(floats) / len(floats)
            r_min = fd.value_range["min"] if fd.value_range else min_v
            r_max = fd.value_range["max"] if fd.value_range else max_v
            if r_min == r_max:
                r_max = r_min + 1.0
            step = (r_max - r_min) / 5
            buckets = []
            for i in range(5):
                low = r_min + i * step
                high = r_min + (i + 1) * step
                count = sum(
                    1 for f in floats
                    if (low <= f < high) or (i == 4 and f == high)
                )
                buckets.append(NumericBucket(range=f"{low:.1f}–{high:.1f}", count=count))
            dist = NumericDistribution(
                min=round(min_v, 2),
                max=round(max_v, 2),
                mean=round(mean_v, 2),
                buckets=buckets,
            )

        distributions.append(
            FeatureDistribution(
                feature_key=fd.key,
                display_name=fd.display_name,
                category=fd.category,
                value_type=fd.value_type,
                distribution=dist,
            )
        )

    return StatsResponse(
        subject_id=subject_id,
        total_students=total,
        feature_distributions=distributions,
    )
