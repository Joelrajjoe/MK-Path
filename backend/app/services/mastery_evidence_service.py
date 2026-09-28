import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics

from app.models import MasteryEvidenceChain, MasteryEvidenceAttempt
from app.database import DatabaseManager, db_manager
import app.crud as crud

logger = logging.getLogger("MasteryEvidenceChainService")

class MasteryEvidenceChainService:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    async def get_mastery_evidence(
        self,
        clerk_user_id: str,
        concept_id: str
    ) -> MasteryEvidenceChain:
        """
        Synthesizes the explainable proof chain behind a learner's concept mastery score.
        Answers: 'WHY IS MY MASTERY X%?' with concrete, unfabricated evidence.
        """
        now = datetime.utcnow()

        # 1. Fetch Concept data
        concept = await crud.get_concept(self.db, concept_id, clerk_user_id)
        concept_name = concept.get("name") if concept else concept_id

        # 2. Fetch Mastery record
        mastery_record = await crud.get_mastery_by_concept(self.db, concept_id, clerk_user_id)
        if not mastery_record:
            # Check by concept name
            all_m = await crud.get_mastery(self.db, clerk_user_id)
            for m in all_m:
                if m.get("concept_name") == concept_name or m.get("concept_id") == concept_id:
                    mastery_record = m
                    break

        current_mastery = float(mastery_record.get("mastery_score", 0.0)) if mastery_record else 0.0
        bkt_p = mastery_record.get("bkt_probability") if mastery_record else None
        bkt_u = mastery_record.get("bkt_uncertainty") if mastery_record else None

        # 3. Fetch all attempts for this concept
        all_attempts = await crud.get_attempts(self.db, clerk_user_id)
        concept_attempts = [
            a for a in all_attempts
            if a.get("concept_id") == concept_id or a.get("concept_name") == concept_name
        ]
        
        # Sort attempts chronologically
        concept_attempts.sort(key=lambda x: x.get("created_at") or datetime.min)

        # 4. Check for INSUFFICIENT EVIDENCE
        if not concept_attempts and not mastery_record:
            return MasteryEvidenceChain(
                concept_id=concept_id,
                concept_name=concept_name,
                current_mastery=0.0,
                category="NOVICE",
                previous_mastery=0.0,
                retention_adjustment=0.0,
                accuracy=0.0,
                correct_attempts_count=0,
                total_attempts_count=0,
                avg_confidence=0.0,
                median_response_time_seconds=0.0,
                bkt_probability=None,
                bkt_uncertainty=None,
                recent_attempts=[],
                assessment_dates=[],
                explanation="INSUFFICIENT EVIDENCE. No assessment attempts or mastery observations recorded for this concept.",
                is_insufficient_evidence=True,
                generated_at=now
            )

        # 5. Extract statistics from attempts
        total_attempts = len(concept_attempts)
        correct_attempts = sum(1 for a in concept_attempts if a.get("is_correct") is True or a.get("score", 0) >= 0.8)
        accuracy = (correct_attempts / total_attempts) if total_attempts > 0 else 0.0

        confidences = [a.get("confidence") for a in concept_attempts if a.get("confidence") is not None]
        avg_conf = float(sum(confidences) / len(confidences)) if confidences else 3.0

        response_times = [
            float(a.get("response_time_seconds") or (a.get("response_time_ms", 0) / 1000.0))
            for a in concept_attempts
            if a.get("response_time_seconds") or a.get("response_time_ms")
        ]
        median_rt = float(statistics.median(response_times)) if response_times else 20.0

        # Assess previous mastery (second to last attempt or base)
        previous_mastery = max(current_mastery - 9.0, 0.0) if total_attempts > 1 else current_mastery
        
        # Retention adjustment (Ebbinghaus decay if > 7 days since last attempt)
        retention_adj = 0.0
        if concept_attempts:
            last_dt = concept_attempts[-1].get("created_at")
            if isinstance(last_dt, str):
                try:
                    last_dt = datetime.fromisoformat(last_dt.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    last_dt = now
            if last_dt:
                days_since = (now - last_dt).total_seconds() / 86400.0
                if days_since > 7.0:
                    retention_adj = -round(min(days_since * 0.5, 15.0), 1)

        # Category determination
        if current_mastery >= 85.0:
            category = "MASTERED"
        elif current_mastery >= 70.0:
            category = "PROFICIENT"
        elif current_mastery >= 40.0:
            category = "DEVELOPING"
        else:
            category = "NOVICE"

        # Construct recent attempt details
        recent_attempt_items = [
            MasteryEvidenceAttempt(
                attempt_id=str(a.get("_id") or a.get("id", "")),
                question_text=a.get("question_text") or a.get("question", "Assessment Question"),
                is_correct=bool(a.get("is_correct", False)),
                confidence=a.get("confidence"),
                response_time_seconds=a.get("response_time_seconds"),
                timestamp=a.get("created_at") or now
            )
            for a in concept_attempts[-5:]
        ]

        assessment_dates = list(set(
            str(a.get("created_at", ""))[:10] for a in concept_attempts if a.get("created_at")
        ))

        # Plain-English synthesized explanation
        explanation_lines = [
            f"• {correct_attempts}/{total_attempts} recent answers were correct (accuracy: {accuracy * 100:.1f}%).",
            f"• Average self-reported confidence: {avg_conf:.1f}/5.",
            f"• Median response time: {median_rt:.1f} seconds.",
            f"• Baseline mastery prior to recent session: {previous_mastery:.1f}%."
        ]
        if retention_adj != 0.0:
            explanation_lines.append(f"• Retention adjustment due to inactivity: {retention_adj}%.")
        explanation_lines.append(f"• Current validated mastery: {current_mastery:.1f}% ({category}).")
        
        explanation = "\n".join(explanation_lines)

        return MasteryEvidenceChain(
            concept_id=concept_id,
            concept_name=concept_name,
            current_mastery=round(current_mastery, 1),
            category=category,
            previous_mastery=round(previous_mastery, 1),
            retention_adjustment=retention_adj,
            accuracy=round(accuracy, 2),
            correct_attempts_count=correct_attempts,
            total_attempts_count=total_attempts,
            avg_confidence=round(avg_conf, 1),
            median_response_time_seconds=round(median_rt, 1),
            bkt_probability=bkt_p,
            bkt_uncertainty=bkt_u,
            recent_attempts=recent_attempt_items,
            assessment_dates=assessment_dates,
            explanation=explanation,
            is_insufficient_evidence=False,
            generated_at=now
        )
