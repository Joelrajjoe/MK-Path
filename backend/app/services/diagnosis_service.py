import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models import DiagnosisType, DiagnosisEvidence, LearningDiagnosis
from app.database import DatabaseManager, db_manager
import app.crud as crud

logger = logging.getLogger("LearningDiagnosisService")

class LearningDiagnosisService:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    async def diagnose_learner(
        self,
        user_id: str,
        concept_id: str,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        correct_answer: Optional[str] = None,
        confidence: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        prerequisites: Optional[List[str]] = None,
        bkt_probability: Optional[float] = None,
        bkt_uncertainty: Optional[float] = None,
        persist: bool = True
    ) -> LearningDiagnosis:
        """
        Diagnoses WHY a learner is experiencing weakness or cognitive mismatch on a concept.
        Strictly deterministic, evidence-based, without emotional or mental-state inference.
        Never fabricates a misconception or jumps to prerequisite failure without evidence.
        """
        now = datetime.utcnow()
        
        # 1. Fetch concept & graph prerequisites if not provided
        if not prerequisites:
            concept_data = await crud.get_concept(self.db, concept_id, user_id)
            if concept_data and "prerequisites" in concept_data:
                prerequisites = concept_data.get("prerequisites", [])
            else:
                prerequisites = []

        # 2. Fetch user's historical attempts on this concept
        all_attempts = await crud.get_attempts(self.db, user_id)
        attempts = [
            a for a in all_attempts 
            if a.get("concept_id") == concept_id or (a.get("concept_name") == concept_id)
        ]
        
        # 3. Fetch user's mastery for this concept
        mastery_record = await crud.get_mastery_by_concept(self.db, concept_id, user_id)
        current_mastery = mastery_record.get("mastery_score", 0.0) if mastery_record else 0.0
        last_reviewed_str = mastery_record.get("last_reviewed") if mastery_record else None
        
        # 4. Fetch prerequisite masteries
        prereq_masteries: Dict[str, float] = {}
        for prereq in (prerequisites or []):
            p_rec = await crud.get_mastery_by_concept(self.db, prereq, user_id)
            prereq_masteries[prereq] = p_rec.get("mastery_score", 0.0) if p_rec else 0.0

        total_attempts = len(attempts)
        is_correct = (answer == correct_answer) if (answer is not None and correct_answer is not None) else None

        # Build base evidence object
        evidence = DiagnosisEvidence(
            attempt_count=total_attempts,
            accuracy=sum(1 for a in attempts if a.get("is_correct")) / max(total_attempts, 1) if attempts else (1.0 if is_correct else 0.0),
            avg_confidence=float(confidence) if confidence is not None else 3.0,
            avg_response_time_seconds=(response_time_ms / 1000.0) if response_time_ms else 0.0,
            bkt_probability=bkt_probability,
            bkt_uncertainty=bkt_uncertainty,
            days_since_review=None,
            prerequisite_states=prereq_masteries,
            recurring_distractor_indices=[]
        )

        # ----------------------------------------------------
        # Evaluation Rules:
        # ----------------------------------------------------

        # Rule 1: INSUFFICIENT_EVIDENCE
        # If there are fewer than 2 attempts and no established mastery/BKT probability, we cannot reliably infer root cause.
        if total_attempts < 2 and bkt_probability is None and not mastery_record:
            diag = LearningDiagnosis(
                clerk_user_id=user_id,
                diagnosis_type=DiagnosisType.INSUFFICIENT_EVIDENCE,
                target_concept=concept_id,
                concept_id=concept_id,
                suspected_root_concept=None,
                evidence=evidence,
                confidence=0.3,
                reason="Only 1 single attempt observed with no prior mastery history. More interaction data is required to isolate misconception or prerequisite weakness.",
                recommended_action=f"Practice 2-3 more questions on '{concept_id}' to establish an accurate diagnostic pattern.",
                timestamp=now
            )
            if persist:
                await crud.create_diagnosis(self.db, diag)
            return diag

        # Rule 2: CONFIDENCE_MISMATCH (Dunning-Kruger or Blind Guessing)
        # High confidence (>=4 out of 5) but incorrect answer, or Low confidence (<=2) with rapid correct answer
        if confidence is not None and is_correct is not None:
            if confidence >= 4 and not is_correct:
                diag = LearningDiagnosis(
                    clerk_user_id=user_id,
                    diagnosis_type=DiagnosisType.CONFIDENCE_MISMATCH,
                    target_concept=concept_id,
                    concept_id=concept_id,
                    suspected_root_concept=concept_id,
                    evidence=evidence,
                    confidence=0.88,
                    reason=f"High confidence ({confidence}/5) paired with an incorrect response indicates an undetected cognitive blindspot or overconfidence.",
                    recommended_action=f"Review targeted solution explanations for '{concept_id}' and compare contrasting examples.",
                    timestamp=now
                )
                if persist:
                    await crud.create_diagnosis(self.db, diag)
                return diag
            elif confidence <= 2 and is_correct and (response_time_ms is not None and response_time_ms < 5000):
                diag = LearningDiagnosis(
                    clerk_user_id=user_id,
                    diagnosis_type=DiagnosisType.CONFIDENCE_MISMATCH,
                    target_concept=concept_id,
                    concept_id=concept_id,
                    suspected_root_concept=concept_id,
                    evidence=evidence,
                    confidence=0.75,
                    reason=f"Low confidence ({confidence}/5) on a correct fast answer ({response_time_ms}ms) suggests second-guessing or intuitive guessing without conceptual certainty.",
                    recommended_action=f"Reinforce self-efficacy on '{concept_id}' through confidence-calibrated active recall.",
                    timestamp=now
                )
                if persist:
                    await crud.create_diagnosis(self.db, diag)
                return diag

        # Rule 3: RETENTION_DECAY
        # High historical mastery (>= 65%) but last reviewed > 7 days ago and current response is incorrect or low BKT
        if last_reviewed_str and current_mastery >= 65.0:
            try:
                if isinstance(last_reviewed_str, str):
                    last_reviewed_dt = datetime.fromisoformat(last_reviewed_str.replace("Z", "+00:00"))
                else:
                    last_reviewed_dt = last_reviewed_str
                days_since = (now - last_reviewed_dt.replace(tzinfo=None)).total_seconds() / 86400.0
                evidence.days_since_review = days_since
                if days_since >= 7.0 and is_correct is False:
                    diag = LearningDiagnosis(
                        clerk_user_id=user_id,
                        diagnosis_type=DiagnosisType.RETENTION_DECAY,
                        target_concept=concept_id,
                        concept_id=concept_id,
                        suspected_root_concept=concept_id,
                        evidence=evidence,
                        confidence=0.85,
                        reason=f"Concept had strong historical mastery ({current_mastery:.1f}%), but has not been practiced in {int(days_since)} days. Performance drop aligns with Ebbinghaus memory decay.",
                        recommended_action=f"Schedule spaced repetition refresher for '{concept_id}' to consolidate long-term memory trace.",
                        timestamp=now
                    )
                    if persist:
                        await crud.create_diagnosis(self.db, diag)
                    return diag
            except Exception as e:
                logger.warning(f"Error parsing last_reviewed timestamp: {e}")

        # Rule 4: PREREQUISITE_WEAKNESS
        # Multiple attempts on target concept failing, AND one or more explicit prerequisite concepts have mastery < 65%
        if prerequisites and total_attempts >= 2 and (is_correct is False or current_mastery < 60.0):
            weak_prereqs = [p for p, m in prereq_masteries.items() if m < 65.0]
            if weak_prereqs:
                weakest_prereq = min(weak_prereqs, key=lambda p: prereq_masteries[p])
                diag = LearningDiagnosis(
                    clerk_user_id=user_id,
                    diagnosis_type=DiagnosisType.PREREQUISITE_WEAKNESS,
                    target_concept=concept_id,
                    concept_id=concept_id,
                    suspected_root_concept=weakest_prereq,
                    evidence=evidence,
                    confidence=0.86,
                    reason=f"Struggles on '{concept_id}' are rooted in prerequisite '{weakest_prereq}', which currently stands at {prereq_masteries[weakest_prereq]:.1f}% mastery.",
                    recommended_action=f"Halt direct drill on '{concept_id}' and remediate foundational concept '{weakest_prereq}' to 80%+ mastery.",
                    timestamp=now
                )
                if persist:
                    await crud.create_diagnosis(self.db, diag)
                return diag

        # Rule 5: RECURRING_MISCONCEPTION
        # Detect if the learner consistently selects the same wrong answer/distractor across multiple attempts
        if total_attempts >= 2 and is_correct is False:
            wrong_answers = [
                str(a.get("selected_option_index") if a.get("selected_option_index") is not None else (a.get("selected_answer") or a.get("answer"))) 
                for a in attempts 
                if (a.get("is_correct") is False or a.get("score", 0) < 0.5) and (a.get("selected_option_index") is not None or a.get("selected_answer") or a.get("answer"))
            ]
            if answer is not None:
                wrong_answers.append(str(answer))
            
            if wrong_answers:
                from collections import Counter
                counts = Counter(wrong_answers)
                most_common_ans, freq = counts.most_common(1)[0]
                if freq >= 2 and most_common_ans not in ["None", ""]:
                    diag = LearningDiagnosis(
                        clerk_user_id=user_id,
                        diagnosis_type=DiagnosisType.RECURRING_MISCONCEPTION,
                        target_concept=concept_id,
                        concept_id=concept_id,
                        suspected_root_concept=concept_id,
                        evidence=evidence,
                        confidence=0.90,
                        reason=f"Learner has repeatedly chosen the same distractor pattern '{most_common_ans}' ({freq} times) when answering questions on '{concept_id}'.",
                        recommended_action=f"Present counter-example exercises specifically designed to refute misconception '{most_common_ans}'.",
                        timestamp=now
                    )
                    if persist:
                        await crud.create_diagnosis(self.db, diag)
                    return diag

        # Rule 6: CONCEPT_WEAKNESS (Direct misunderstanding of the target concept)
        if current_mastery < 70.0 or is_correct is False or (bkt_probability is not None and bkt_probability < 0.65):
            diag = LearningDiagnosis(
                clerk_user_id=user_id,
                diagnosis_type=DiagnosisType.CONCEPT_WEAKNESS,
                target_concept=concept_id,
                concept_id=concept_id,
                suspected_root_concept=concept_id,
                evidence=evidence,
                confidence=0.80,
                reason=f"Direct conceptual gap on '{concept_id}'. Prerequisite foundations are intact, indicating need for core instructional drill.",
                recommended_action=f"Engage in step-by-step interactive practice with immediate feedback on '{concept_id}'.",
                timestamp=now
            )
            if persist:
                await crud.create_diagnosis(self.db, diag)
            return diag

        # Fallback
        diag = LearningDiagnosis(
            clerk_user_id=user_id,
            diagnosis_type=DiagnosisType.INSUFFICIENT_EVIDENCE,
            target_concept=concept_id,
            concept_id=concept_id,
            suspected_root_concept=None,
            evidence=evidence,
            confidence=0.5,
            reason=f"No systemic misconception or prerequisite gap detected for '{concept_id}'. Performance is on track.",
            recommended_action=f"Continue progressive difficulty advancement on '{concept_id}'.",
            timestamp=now
        )
        if persist:
            await crud.create_diagnosis(self.db, diag)
        return diag
