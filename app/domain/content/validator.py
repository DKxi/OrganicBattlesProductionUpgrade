import re
from typing import List, Dict, Any, Optional, Tuple

SAFE_IMAGE_REGEX = re.compile(r"^[\w\-\–\—]+\.(png|jpg|jpeg|svg|webp)$", re.IGNORECASE | re.UNICODE)


class QuestionValidationError(ValueError):
    """Raised when question schema, choices, spells, health, or images fail validation."""
    def __init__(self, message: str, *args):
        super().__init__(message, *args)
        try:
            from app.observability.metrics import metrics_registry
            metrics_registry.record_ingestion_validation_failure({"error": message})
        except Exception:
            pass


def validate_question_payload(
    options: Any,
    correct_option: str,
    correct_answer: str,
    spells: Optional[Any] = None,
    health: Optional[Any] = None,
    images: Optional[Any] = None,
) -> Tuple[List[Dict[str, str]], str, str, List[int], List[int], List[str]]:
    """
    Validate and normalize question choices, answer keys, spells, health, and images.
    Enforces:
    1. Every question has at least two choices.
    2. Option labels are valid and unique.
    3. Exactly one correct option exists.
    4. correct_option corresponds to the correct answer.
    5. Health and spell values are valid positive numbers.
    6. Image filenames are safe and recognized.
    """
    # 1. Validate options array
    if not isinstance(options, list) or len(options) < 2:
        raise QuestionValidationError("Every question must have at least two choices.")

    formatted_options: List[Dict[str, str]] = []
    labels: List[str] = []

    for idx, opt in enumerate(options):
        if not isinstance(opt, dict):
            raise QuestionValidationError(f"Option at index {idx} must be an object with 'label' and 'text'.")

        lbl = str(opt.get("label", "")).strip()
        txt = str(opt.get("text", "")).strip()

        if not lbl:
            raise QuestionValidationError(f"Option at index {idx} has an empty label.")
        if not txt:
            raise QuestionValidationError(f"Option '{lbl}' has empty choice text.")

        if lbl in labels:
            raise QuestionValidationError(f"Option label '{lbl}' is duplicated. Option labels must be unique.")

        labels.append(lbl)
        formatted_options.append({"label": lbl, "text": txt})

    # 2. Validate correct_option and correct_answer
    c_opt = str(correct_option).strip() if correct_option else ""
    if not c_opt:
        raise QuestionValidationError("correct_option is required.")

    c_ans = str(correct_answer).strip() if correct_answer else ""
    if not c_ans:
        raise QuestionValidationError("correct_answer is required.")

    matching_options = [opt for opt in formatted_options if opt["label"] == c_opt]
    if len(matching_options) != 1:
        raise QuestionValidationError(
            f"Exactly one correct option must exist. Specified correct_option '{c_opt}' matched {len(matching_options)} options."
        )

    matched_opt = matching_options[0]
    if matched_opt["text"].strip().lower() != c_ans.strip().lower():
        raise QuestionValidationError(
            f"correct_option '{c_opt}' text ('{matched_opt['text']}') does not correspond to correct_answer ('{c_ans}')."
        )

    # 3. Validate spells (if provided)
    formatted_spells: List[int] = [20, 30, 45]
    if spells is not None:
        if not isinstance(spells, list) or len(spells) == 0:
            raise QuestionValidationError("Spell values must be a non-empty list of positive numbers.")
        formatted_spells = []
        for s in spells:
            if not isinstance(s, (int, float)) or s <= 0:
                raise QuestionValidationError(f"Invalid spell value '{s}'. Spell values must be positive numbers.")
            formatted_spells.append(int(s))

    # 4. Validate health (if provided)
    formatted_health: List[int] = [100]
    if health is not None:
        if not isinstance(health, list) or len(health) == 0:
            raise QuestionValidationError("Health values must be a non-empty list of positive numbers.")
        formatted_health = []
        for h in health:
            if not isinstance(h, (int, float)) or h <= 0:
                raise QuestionValidationError(f"Invalid health value '{h}'. Health values must be positive numbers.")
            formatted_health.append(int(h))

    # 5. Validate images (if provided)
    formatted_images: List[str] = []
    if images is not None:
        if not isinstance(images, list):
            raise QuestionValidationError("Images must be a list of safe filenames.")
        for img in images:
            img_str = str(img).strip()
            if not img_str:
                continue
            if "/" in img_str or "\\" in img_str or ".." in img_str:
                raise QuestionValidationError(f"Unsafe image path '{img_str}'. Path traversal is strictly prohibited.")
            if not SAFE_IMAGE_REGEX.match(img_str):
                raise QuestionValidationError(
                    f"Image filename '{img_str}' is invalid. Must be a recognized image format (.png, .jpg, .jpeg, .svg, .webp)."
                )
            formatted_images.append(img_str)

    return formatted_options, c_opt, c_ans, formatted_spells, formatted_health, formatted_images
