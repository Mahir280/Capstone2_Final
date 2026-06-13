"""TF-IDF feature extraction for saved patent records."""

from dataclasses import dataclass

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from src.models.patent import PatentRecord


@dataclass(slots=True)
class TfidfTopTerm:
    """A TF-IDF term score for one patent row."""

    term: str
    score: float


@dataclass(slots=True)
class TfidfFeatureResult:
    """Structured output from the TF-IDF baseline."""

    analysis_ids: list[str]
    patent_ids: list[str]
    matrix_shape: tuple[int, int]
    feature_names: list[str]
    matrix: csr_matrix | None = None
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        """Return whether usable TF-IDF features were produced."""
        return self.error is None and self.matrix is not None

    @property
    def vocabulary_size(self) -> int:
        """Return the number of extracted vocabulary terms."""
        return len(self.feature_names)


class TfidfFeatureService:
    """Build baseline TF-IDF features from canonical patent records."""

    def build_from_patents(
        self,
        records: list[PatentRecord],
        *,
        max_features: int | None = None,
        ngram_range: tuple[int, int] = (1, 1),
    ) -> TfidfFeatureResult:
        """Build TF-IDF features from patent title, abstract, and keywords."""
        if not records:
            return TfidfFeatureResult(
                analysis_ids=[],
                patent_ids=[],
                matrix_shape=(0, 0),
                feature_names=[],
                error="No saved patents are available for TF-IDF analysis.",
            )

        analysis_ids = [record.analysis_id for record in records]
        patent_ids = [record.patent_id for record in records]
        analysis_texts = [build_combined_analysis_text(record) for record in records]
        if not any(analysis_texts):
            return TfidfFeatureResult(
                analysis_ids=analysis_ids,
                patent_ids=patent_ids,
                matrix_shape=(len(records), 0),
                feature_names=[],
                error=(
                    "Saved patents do not contain title, abstract, or keywords "
                    "for TF-IDF analysis."
                ),
            )

        try:
            vectorizer = TfidfVectorizer(
                max_features=max_features,
                ngram_range=ngram_range,
                stop_words="english",
            )
            matrix = vectorizer.fit_transform(analysis_texts).tocsr()
        except ValueError as exc:
            return TfidfFeatureResult(
                analysis_ids=analysis_ids,
                patent_ids=patent_ids,
                matrix_shape=(len(records), 0),
                feature_names=[],
                error=f"TF-IDF analysis could not be built: {exc}",
            )

        feature_names = list(vectorizer.get_feature_names_out())
        return TfidfFeatureResult(
            analysis_ids=analysis_ids,
            patent_ids=patent_ids,
            matrix_shape=matrix.shape,
            feature_names=feature_names,
            matrix=matrix,
        )

    def top_terms_for_patent(
        self,
        result: TfidfFeatureResult,
        analysis_id: str,
        top_n: int = 10,
    ) -> list[TfidfTopTerm]:
        """Return the highest-scoring TF-IDF terms for one patent row."""
        if not result.is_valid or result.matrix is None or top_n <= 0:
            return []

        try:
            row_index = result.analysis_ids.index(analysis_id)
        except ValueError:
            return []

        row = result.matrix.getrow(row_index)
        terms = [
            TfidfTopTerm(
                term=result.feature_names[feature_index],
                score=float(score),
            )
            for feature_index, score in zip(row.indices, row.data, strict=True)
            if score > 0
        ]
        return sorted(terms, key=lambda item: (-item.score, item.term))[:top_n]


def build_combined_analysis_text(record: PatentRecord) -> str:
    """Build deterministic TF-IDF input from title, abstract, and keywords."""
    keyword_text = " ".join(_clean_text(keyword) for keyword in record.keywords)
    parts = [
        _clean_text(record.title),
        _clean_text(record.abstract),
        _clean_text(keyword_text),
    ]
    return "\n\n".join(part for part in parts if part)


def _clean_text(value: str | None) -> str:
    return " ".join(value.split()) if value else ""
