from vespa.package import (
    ApplicationPackage,
    Component,
    Document,
    Field,
    FieldSet,
    Function,
    GlobalPhaseRanking,
    HNSW,
    Parameter,
    RankProfile,
    Schema,
)


TENANT = "agentic-search"

# IMPORTANT:
# Keep the existing tutorial application untouched.
# The job system uses a separate Vespa Cloud instance.
APPLICATION = "agenticjobsearch"
INSTANCE = "jobs-clean"


package = ApplicationPackage(
    name=APPLICATION,

    schema=[
        Schema(
            name="job",

            document=Document(
                fields=[

                    # ------------------------------------------------
                    # Stable job identifier
                    # ------------------------------------------------
                    Field(
                        name="job_id",
                        type="string",
                        indexing=[
                            "summary",
                            "attribute",
                        ],
                    ),

                    # ------------------------------------------------
                    # Job title
                    # ------------------------------------------------
                    Field(
                        name="title",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                        index="enable-bm25",
                    ),

                    # ------------------------------------------------
                    # Company
                    # ------------------------------------------------
                    Field(
                        name="company",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                        index="enable-bm25",
                    ),

                    # ------------------------------------------------
                    # Full job description
                    # ------------------------------------------------
                    Field(
                        name="description",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                        index="enable-bm25",
                    ),

                    # ------------------------------------------------
                    # Normalized skills
                    # ------------------------------------------------
                    Field(
                        name="skills",
                        type="array<string>",
                        indexing=[
                            "index",
                            "summary",
                            "attribute",
                        ],
                    ),

                    # ------------------------------------------------
                    # Location
                    # ------------------------------------------------
                    Field(
                        name="location",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                        index="enable-bm25",
                    ),

                    # ------------------------------------------------
                    # Experience
                    # ------------------------------------------------
                    Field(
                        name="experience",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                    ),

                    # ------------------------------------------------
                    # Employment type
                    # ------------------------------------------------
                    Field(
                        name="employment_type",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                    ),

                    # ------------------------------------------------
                    # Salary
                    # ------------------------------------------------
                    Field(
                        name="salary",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                    ),

                    # ------------------------------------------------
                    # Original URL
                    # ------------------------------------------------
                    Field(
                        name="url",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                        index="enable-bm25",
                    ),

                    # ------------------------------------------------
                    # Combined retrieval text
                    #
                    # This will be populated by job_feed.py.
                    #
                    # title + company + skills + location +
                    # experience + employment_type + description
                    # ------------------------------------------------
                    Field(
                        name="search_text",
                        type="string",
                        indexing=[
                            "index",
                            "summary",
                        ],
                        index="enable-bm25",
                    ),

                    # ------------------------------------------------
                    # Semantic embedding
                    # ------------------------------------------------
                    Field(
                        name="text_embedding",
                        type="tensor<float>(x[384])",
                        indexing=[
                            "input search_text",
                            "embed",
                            "index",
                            "attribute",
                        ],
                        ann=HNSW(
                            distance_metric="angular"
                        ),
                        is_document_field=False,
                    ),
                ]
            ),

            fieldsets=[
                FieldSet(
                    name="default",
                    fields=[
                        "title",
                        "company",
                        "description",
                        "skills",
                        "location",
                        "experience",
                        "employment_type",
                        "search_text",
                        "url",
                    ],
                ),
            ],

            rank_profiles=[

                # ====================================================
                # BM25
                # ====================================================
                RankProfile(
                    name="bm25",

                    functions=[
                        Function(
                            name="bm25search",
                            expression=(
                                "bm25(search_text)"
                            ),
                        ),
                    ],

                    first_phase=(
                        "bm25search"
                    ),
                ),

                # ====================================================
                # Semantic
                # ====================================================
                RankProfile(
                    name="semantic",

                    inputs=[
                        (
                            "query(q)",
                            "tensor<float>(x[384])",
                        ),
                    ],

                    first_phase=(
                        "closeness("
                        "field, "
                        "text_embedding"
                        ")"
                    ),
                ),

                # ====================================================
                # Raw hybrid
                # ====================================================
                RankProfile(
                    name="hybrid",

                    inputs=[
                        (
                            "query(q)",
                            "tensor<float>(x[384])",
                        ),
                    ],

                    functions=[
                        Function(
                            name="bm25search",
                            expression=(
                                "bm25(search_text)"
                            ),
                        ),

                        Function(
                            name="semantic_score",
                            expression=(
                                "closeness("
                                "field, "
                                "text_embedding"
                                ")"
                            ),
                        ),
                    ],

                    first_phase=(
                        "0.5 * bm25search + "
                        "0.5 * semantic_score"
                    ),
                ),

                # ====================================================
                # RRF
                # ====================================================
                RankProfile(
                    name="rrf",

                    inherits="bm25",

                    inputs=[
                        (
                            "query(q)",
                            "tensor<float>(x[384])",
                        ),
                    ],

                    functions=[
                        Function(
                            name="semantic_score",
                            expression=(
                                "closeness("
                                "field, "
                                "text_embedding"
                                ")"
                            ),
                        ),
                    ],

                    first_phase=(
                        "semantic_score"
                    ),

                    global_phase=GlobalPhaseRanking(
                        expression=(
                            "reciprocal_rank_fusion("
                            "bm25search, "
                            "semantic_score"
                            ")"
                        ),
                        rerank_count=100,
                    ),
                ),
            ],
        )
    ],

    components=[
        Component(
            id="e5",
            type="hugging-face-embedder",

            parameters=[
                Parameter(
                    "transformer-model",
                    {
                        "model-id": "e5-small-v2",
                    },
                ),

                Parameter(
                    "prepend",
                    {},

                    children=[
                        Parameter(
                            "query",
                            {},
                            "query: ",
                        ),

                        Parameter(
                            "document",
                            {},
                            "passage: ",
                        ),
                    ],
                ),
            ],
        )
    ],
)