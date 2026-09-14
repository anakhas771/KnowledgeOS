"""
Long-form source documents for the evaluation-only chunking experiment.

The existing retrieval evaluation corpus (``seed_retrieval_evaluation``) writes
two hand-authored chunks per document straight into ``DocumentChunk``, bypassing
the chunker entirely. That is deliberate for controlled ranking tests, but it
makes chunk-size and overlap unmeasurable: every configuration would produce a
single chunk.

These documents are long enough (~2.5-3.5k characters) that the production
chunker yields materially different chunk counts across the configurations under
test, while keeping the exact document titles used by ``EVALUATION_CASES`` so the
existing query set — including single-document and multi-relevant queries —
remains valid without modification.

The text is a fixed literal: identical for every configuration and every run, so
chunking is the only thing that varies.
"""

from __future__ import annotations

SOURCE_DOCUMENTS: dict[str, str] = {
    "KnowledgeOS Overview": """
KnowledgeOS Platform Overview

KnowledgeOS is an enterprise knowledge intelligence platform that centralizes
organizational knowledge and provides semantic search and AI-assisted answers.
It is designed for organizations whose institutional knowledge is scattered
across documents, wikis, spreadsheets, and slide decks, where employees cannot
reliably find an authoritative answer to an ordinary question.

Purpose and scope

The platform ingests documents that an organization already owns, converts them
into a retrieval-ready form, and exposes that knowledge through a search
interface and a question-answering assistant. KnowledgeOS does not attempt to
replace the systems of record where documents originate. It builds a retrieval
layer over them so that knowledge locked inside long files becomes reachable.

Core technology

KnowledgeOS uses document ingestion, text extraction, chunking, vector
embeddings, PostgreSQL with pgvector, and local language-model generation. Text
is extracted from uploaded files, normalized, divided into retrieval units, and
converted into dense vector representations. Those vectors are stored next to
the text they represent and searched using cosine similarity.

Generation is grounded. When the assistant answers a question it first retrieves
supporting chunks from the organization's own documents and then conditions the
language model on that retrieved context. The model is not asked to recall
company facts from its training data, because it has none. This grounding is
what separates KnowledgeOS from a general-purpose chat assistant.

Operational characteristics

Document processing runs asynchronously through a task queue, so uploading a
large file does not block the request that submitted it. Retrieval is filtered
by organization on every query, which keeps one tenant's knowledge invisible to
another. Embeddings are produced by a dedicated service so the model that
generates them can be upgraded independently of the application.

Intended outcomes

The platform aims to reduce the time employees spend searching for information
that the organization already documented, to reduce duplicated effort caused by
knowledge that cannot be found, and to give answers that cite the documents they
came from rather than asserting facts without provenance.
""",
    "Authentication and RBAC": """
Authentication and Role-Based Access Control

KnowledgeOS authentication uses JWT-based authentication for API access. Users
authenticate before accessing protected knowledge endpoints. Authentication
establishes who is making a request; it does not by itself decide what that
requester is permitted to do.

Token-based authentication

A client exchanges credentials for a signed token. Subsequent requests present
that token, and the platform validates its signature and expiry before the
request reaches any knowledge endpoint. Because the token carries the user
identity, the API does not need a server-side session for each caller, which
keeps the authentication path stateless and horizontally scalable.

Tokens are short-lived. A refresh flow issues replacements so that a stolen
token has a bounded useful lifetime. Requests presenting an expired, malformed,
or unsigned token are rejected before any document or chunk is read.

Organization roles

KnowledgeOS supports organization roles including administrator, manager,
developer, employee, and guest. Role-based permissions control access to
protected actions. The administrator role manages organization configuration
and membership. Managers and developers operate the knowledge base and its
ingestion pipeline. The employee role covers ordinary knowledge consumption:
search and question answering. The guest role is deliberately narrow and is
intended for limited or time-boxed access.

Separation of identity from permission

Role checks happen after authentication succeeds. A valid token proves identity
and nothing more. The permission layer then evaluates whether the identified
user's role allows the requested action. Keeping these two concerns separate
means an authentication change, such as adopting a new token format, does not
require rewriting permission rules, and adding a role does not weaken identity
verification.

Interaction with tenancy

The authenticated user also determines the tenant context for retrieval. The
organization is read from the user record rather than accepted from the request,
so a caller cannot widen their own access by naming a different organization.
Authentication, authorization, and tenant scoping therefore compose: identity is
verified, permission is checked, and results are filtered to the caller's
organization.
""",
    "Document Processing": """
Document Processing Pipeline

Uploaded documents are processed asynchronously. The processing pipeline
extracts text, normalizes it, splits the text into chunks, generates embeddings,
and stores retrieval-ready chunks. Each stage has a single responsibility, and a
failure in any stage marks the document as failed with the error recorded for
inspection.

Asynchronous execution

Processing is dispatched to a background worker rather than performed inside the
upload request. A large document can take a long time to extract and embed, and
holding an HTTP connection open for that duration would be fragile. The upload
request therefore returns as soon as the file is stored, and the document moves
through processing states that a client can poll.

Stage one: extraction

Extraction converts the uploaded file into plain text. Document processing
supports common knowledge formats including TXT, Markdown, PDF, DOCX, and XLSX.
Each format has its own reader, because the structure of a spreadsheet and the
structure of a slide deck are not recoverable by the same code path.

Stage two: normalization

Normalization makes extracted text predictable. Line endings are unified,
repeated horizontal whitespace is collapsed to single spaces, and runs of blank
lines are reduced. This matters for retrieval quality: without normalization,
otherwise identical passages extracted from different file formats would produce
different embeddings purely because of incidental whitespace.

Stage three: chunking

Chunking divides the normalized text into retrieval units. A whole document is
usually too large to embed usefully, because a single vector averaged over
thousands of words loses the specific detail a query is looking for. Splitting
the document produces units small enough to represent a focused idea.

Stage four: embedding and storage

Each chunk is converted into a vector by the embedding service, and the chunk
text and its vector are written together with the chunk's ordinal position in
the document. Storing position alongside content preserves reading order, so a
retrieved chunk can be located within its source document.

Failure handling

Any stage may fail. An unreadable file, an empty extraction, a document that
produces no usable chunks, or an embedding service returning the wrong number of
vectors all abort processing. The document is marked failed and the error is
retained, so a failed document is visibly failed rather than silently empty.
""",
    "Tenant Isolation": """
Tenant Isolation

KnowledgeOS enforces tenant isolation by associating documents with an
organization and filtering retrieval queries using the authenticated user's
organization. Isolation is a correctness property of the retrieval layer, not a
feature layered on top of it.

Ownership model

Every document belongs to exactly one organization, and every chunk belongs to
exactly one document. Ownership is therefore unambiguous at both the document
and chunk level, and a chunk's tenant can always be resolved by following its
document relationship.

Server-derived tenant context

Clients do not choose the organization used for knowledge retrieval. The
organization context comes from the authenticated user. This is the central
design decision of the isolation model. If a request could name the organization
to search, then any authenticated user could read another tenant's knowledge by
substituting a different identifier. Deriving the organization from the user
record removes that possibility.

Filtering at the query boundary

Retrieval filters by organization in the database query itself rather than
fetching candidates broadly and discarding foreign results afterwards.
Post-filtering would be both slower and less safe: a similarity search that
retrieves the top matches across all tenants and then removes the ones the
caller may not see can return fewer results than requested, and it briefly
handles data the caller is not entitled to.

Relationship to authorization

Tenant isolation and authorization answer different questions. Authorization
asks whether this user may perform this action. Isolation asks which subset of
knowledge this user's query is allowed to range over. A user may hold a role
permitting search while still being confined to their own organization's
documents, and both checks apply on the same request.

Failure mode being prevented

The specific failure this design prevents is cross-tenant leakage through
semantic search. Vector similarity is content-based and has no notion of
ownership: a query embedding is equally close to a similar chunk regardless of
which organization owns it. Without an explicit organization filter, similarity
alone would happily return another tenant's most relevant passage.
""",
    "Search and Retrieval": """
Search and Retrieval

Semantic search converts a user query into a 384-dimensional embedding and
retrieves similar document chunks using pgvector cosine similarity. Retrieval is
the stage that decides which knowledge a user or an assistant actually sees, so
its behavior determines the quality of everything downstream.

Query embedding

The query is embedded by the same model that embedded the stored chunks. Using
one model for both sides is required for the comparison to be meaningful:
vectors from different models occupy different spaces, and cosine similarity
between them measures nothing.

Similarity computation

Retrieval ranks chunks by cosine similarity, computed as one minus cosine
distance. Cosine similarity compares orientation rather than magnitude, which
suits text embeddings because a passage's meaning should not depend on its
length. Candidate chunks are restricted to the caller's organization before
ranking.

Index structure

KnowledgeOS uses an HNSW vector index to support scalable approximate
nearest-neighbor retrieval while ranking results by similarity. An exact scan
compares the query against every stored vector, which is acceptable for a small
corpus and untenable for a large one. HNSW navigates a layered proximity graph
and inspects a small fraction of the corpus, trading a small amount of recall
for a large reduction in query time.

Result shaping

Retrieval returns chunks, not documents. Because several chunks from the same
document can rank highly, consumers that reason at document level deduplicate
while preserving rank order, keeping each document at the position of its best
chunk. The result payload carries the chunk text, its similarity score, and the
identity and title of its source document, so a caller can cite provenance.

Retrieval strategies

Pure vector similarity is one strategy among several. Lexical search matches
terms directly and is stronger on exact identifiers and rare words. Score fusion
combines normalized semantic and lexical scores under explicit weights, and
reciprocal rank fusion combines the two rankings by position instead of score.
Which strategy wins is an empirical question and is measured against a fixed
evaluation set rather than assumed.
""",
    "Authorization and Permissions": """
Authorization and Permissions

Authorization determines which actions an authenticated KnowledgeOS user may
perform. Permissions are evaluated after authentication and are based on the
user's role. Authorization is the second of two independent gates: the first
establishes identity, the second establishes entitlement.

Ordering of checks

Permission evaluation always follows identity verification. There is no
meaningful way to authorize an unknown caller, because every permission rule is
expressed in terms of a user and their role. A request with an invalid token is
therefore rejected before any permission logic runs.

Role-derived permissions

Role-based authorization separates identity verification from permission checks.
A valid JWT identifies the user, while authorization rules determine access to
protected operations. Permissions are attached to roles rather than to
individual users, which keeps entitlement auditable: reviewing what a role may
do is tractable, whereas reviewing per-user grants across a large organization
is not.

Protected operations

Operations divide into knowledge consumption and knowledge administration.
Consumption covers searching the corpus and asking questions of it.
Administration covers uploading and removing documents, triggering reprocessing,
and managing organization membership. The distinction matters because
administrative actions change what every other user in the organization will
retrieve.

Failing closed

Authorization denies by default. An operation with no explicit rule permitting
it is refused rather than allowed, so adding a new endpoint cannot accidentally
expose it to roles that were never considered. Denials are reported without
disclosing whether the target resource exists, since existence itself can be
sensitive.

Composition with tenancy

Authorization is necessary but not sufficient. A role that permits search
constrains the action, not its scope. The tenant filter independently constrains
which documents the permitted search may range over. Both apply to the same
request, and neither substitutes for the other.
""",
    "Organization Membership": """
Organization Membership

A KnowledgeOS user belongs to an organization. The organization relationship is
stored on the authenticated user and establishes the tenant context for
knowledge access. Membership is the link between an identity and the body of
knowledge that identity may search.

Where membership lives

Membership is recorded on the user record. Because retrieval reads the
organization from that record rather than from request parameters, membership is
the single authoritative source of tenant context. Changing a user's
organization changes what they retrieve, and there is no second place where that
context could disagree.

Membership is not a role

Organization membership is different from application roles. Membership
determines which tenant a user belongs to, while roles determine which protected
actions the user may perform. The two are orthogonal. Two administrators in
different organizations hold identical permissions over entirely disjoint
document sets, and two users in one organization may hold different roles over
the same documents.

Conflating the two concepts is a common source of access-control bugs. Treating
membership as a permission suggests that a sufficiently privileged role could
read across tenants, which the isolation model explicitly forbids. Treating a
role as membership suggests that changing someone's role could move them between
tenants, which it must not.

Effect on retrieval

Every retrieval request resolves the caller's organization from membership and
filters candidate chunks to documents owned by that organization. The filter is
applied in the database query, so results are scoped before ranking rather than
trimmed afterwards.

Lifecycle

Membership changes have immediate retrieval consequences. A user moved between
organizations begins retrieving the new organization's knowledge and stops
retrieving the old, without any reprocessing of documents, because scoping is
evaluated per query rather than baked into stored chunks.
""",
    "Document Extraction": """
Document Extraction

Document extraction converts uploaded files into readable text before downstream
processing. The extracted content becomes the input for normalization and chunk
creation. Extraction is the first stage of ingestion and the only stage that
must understand file formats.

Position in the pipeline

Extraction is an ingestion-stage operation. It prepares content from supported
document formats so the processing pipeline can generate searchable text chunks.
Every later stage — normalization, chunking, embedding, storage — operates on
plain text and is therefore independent of the original file format. Isolating
format knowledge in one stage means support for a new format requires a new
reader and nothing else.

Format-specific readers

Plain text and Markdown are read directly. PDF extraction walks the document's
pages and concatenates their text content. Word documents are read through their
paragraph structure. Spreadsheets are traversed by sheet, row, and cell, with
cell values joined into readable lines. A single generic reader cannot serve
these formats because their internal models differ fundamentally.

What extraction does not do

Extraction does not interpret meaning, rewrite content, or summarize. It also
does not decide retrieval units; that is chunking's responsibility. Keeping
extraction narrow avoids a class of bug where content is silently altered before
anyone can inspect it.

Quality considerations

Extraction quality bounds retrieval quality. Text that a reader mangles cannot
be recovered by a later stage: a garbled passage will be chunked and embedded
faithfully as garble, and it will match queries poorly. Extractions producing no
text at all are treated as failures rather than as empty documents, because an
empty document would otherwise appear successfully processed while contributing
nothing to retrieval.

Scanned and image-only files

A file whose content is an image of text yields no extractable text through
these readers. Such documents fail explicitly rather than being stored as empty,
which makes the gap visible instead of leaving a document that can never be
retrieved.
""",
    "Chunking and Embeddings": """
Chunking and Embeddings

Chunking divides extracted document text into smaller retrieval units. Each
chunk can then be converted into a vector embedding for semantic search. These
two stages together decide the granularity at which knowledge becomes
retrievable.

Why documents are divided

A single embedding for an entire document averages everything the document says.
The specific sentence answering a narrow question contributes only slightly to
that average and is effectively diluted. Dividing the document produces units
whose vectors represent a focused portion of the text, so a specific query can
match the specific passage that answers it.

Chunk size as a trade-off

Chunk size controls a genuine tension. Small chunks give precise matches but may
sever the context needed to interpret them, and they multiply the number of
vectors stored and compared. Large chunks retain context but dilute their own
embeddings, so a long chunk that answers a question in one sentence may rank
below a shorter chunk that is merely on-topic throughout. There is no size that
is correct in the abstract; the appropriate size depends on the corpus and on
the questions asked of it.

Overlap

Overlap repeats a trailing portion of one chunk at the start of the next. Its
purpose is to protect passages that fall across a boundary: without overlap, a
statement split between two chunks appears incomplete in both, and neither
matches a query about it well. Overlap costs storage and adds near-duplicate
candidates that can crowd a result list, so it is a deliberate trade rather than
a free improvement.

Embedding generation

KnowledgeOS stores embeddings alongside document chunks. The embedding
represents the semantic content used for vector similarity retrieval. Chunks are
embedded in batches by a dedicated service, and the number of vectors returned
must match the number of chunks submitted; a mismatch aborts processing rather
than risking a chunk being stored with another chunk's vector.

Ordering and identity

Each chunk records its ordinal position within its document. Position preserves
reading order, allows a retrieved chunk to be located in context, and makes
reprocessing deterministic: the same document and the same configuration produce
the same chunks in the same order.
""",
    "Ingestion Pipeline": """
Ingestion Pipeline

The ingestion pipeline moves uploaded knowledge through extraction,
normalization, chunking, embedding generation, and storage before it becomes
available for retrieval. Ingestion is the boundary between a file an
organization happens to own and knowledge the platform can actually retrieve.

Stage sequence

The stages run in a fixed order, each consuming the previous stage's output.
Extraction produces text from a file. Normalization makes that text uniform.
Chunking divides it into retrieval units. Embedding converts each unit into a
vector. Storage persists units and vectors together. A document is retrievable
only after the final stage completes.

Asynchronous execution

Asynchronous ingestion separates document processing from the request that
uploads the file, allowing retrieval-ready knowledge to be prepared in the
background. This decoupling is what makes large documents practical. It also
means ingestion state is observable: a document is uploaded, processing,
completed, or failed, and clients can poll that state instead of waiting.

Idempotence and reprocessing

Reprocessing a document replaces its chunks rather than adding to them. Existing
chunks are deleted and the new set is written in one transaction, so a document
never presents a mixture of chunks from two different processing runs. This makes
reprocessing safe to repeat and is what allows a chunking configuration to be
changed and re-evaluated.

Transactional storage

Chunk replacement and the document's final state change are committed together.
A crash mid-processing therefore leaves the document in its previous state
rather than in a partially reprocessed one. Without this, an interrupted run
could leave a document marked complete while holding only some of its chunks.

Failure propagation

Failures are not swallowed. A stage that cannot complete records the error on
the document and marks it failed, and the task is retried with backoff for
transient conditions such as the embedding service being briefly unavailable. A
document that repeatedly fails stays visibly failed rather than appearing
complete and empty.
""",
    "Vector Database": """
Vector Database

KnowledgeOS uses PostgreSQL with pgvector to store document embeddings and
perform vector similarity operations. Vectors live in the same database as the
documents and chunks they describe, rather than in a separate specialized store.

Rationale for a single store

Keeping vectors beside relational data means a similarity search can be
expressed as an ordinary query that also joins document metadata and filters by
organization. A separate vector store would require a two-step retrieval —
search vectors remotely, then fetch matching rows locally — and would introduce
a second system that can disagree with the first about what exists. Transactional
consistency between a chunk and its vector comes for free when both are written
in the same transaction.

Storage model

Each chunk row carries a fixed-width vector column of 384 dimensions matching
the embedding model's output, together with the chunk text and its position in
its document. The dimension is fixed at the schema level, so a vector of the
wrong width is rejected on write instead of corrupting later comparisons.

Distance operations

The vector database layer supports cosine-distance searches over document
embeddings and uses an HNSW index for approximate nearest-neighbor retrieval.
Cosine distance compares direction rather than magnitude, which is appropriate
for text embeddings; similarity is derived as one minus that distance so that
larger values mean closer matches.

Approximate indexing

An exact nearest-neighbor search compares the query against every stored vector.
That cost is fine for a small corpus and unacceptable as one grows. The HNSW
index builds a layered graph of proximity links and traverses it, examining a
small fraction of the corpus per query. The result is approximate: a true nearest
neighbor can occasionally be missed, in exchange for a large reduction in query
time. Index build parameters control that trade-off.

Interaction with tenancy

Similarity has no concept of ownership, so the organization filter is part of the
same query that ranks by distance. Candidates are restricted to the caller's
organization before ranking, which is both safer and cheaper than ranking
globally and discarding foreign results afterwards.
""",
    "Semantic Search": """
Semantic Search

Semantic search represents a user's query as an embedding and compares it with
stored document embeddings to identify conceptually similar knowledge. It
retrieves on meaning rather than on the specific words a user happened to type.

Matching on meaning

Semantic retrieval can find relevant content even when the query uses wording
different from the source document. A question about signing in can match a
passage about authentication, and a question about keeping tenants separate can
match a passage about organization filtering, because the embedding model places
related ideas near one another regardless of vocabulary.

Contrast with lexical matching

Lexical search matches terms. It is precise when a query names something exactly
— an error code, a product name, a rare technical term — and it fails when the
query and the document express one idea in different words. Semantic search has
the opposite profile: robust to paraphrase, weaker on exact identifiers, and
capable of confidently returning a passage that is merely on-topic. Their failure
modes are complementary, which is why combining them is worth measuring.

Symmetry requirement

Query and document must be embedded by the same model. Two models produce
vectors in unrelated spaces, and a cosine similarity computed across those spaces
is meaningless rather than merely inaccurate. Changing the embedding model
therefore requires re-embedding the entire corpus, not just new documents.

Known weaknesses

Semantic similarity is not relevance. A chunk discussing the same subject as the
query can rank above the chunk that actually answers it, especially when the
answering chunk is long and covers several subjects. Negation is represented
weakly, so a passage stating that something does not happen may sit close to a
query asking whether it does. These are properties of the representation, not
bugs in the query path.

Evaluation

Because these weaknesses are not visible from inspecting code, retrieval quality
is measured against a fixed set of queries with known relevant documents,
reporting recall at several depths, mean reciprocal rank, precision, and latency.
Changes to retrieval are judged against that baseline rather than by impression.
""",
    "AI Assistant Architecture": """
AI Assistant Architecture

The KnowledgeOS assistant combines retrieved knowledge context with a language
model to generate answers grounded in organizational documents. The assistant is
a consumer of retrieval, not a replacement for it.

Retrieval before generation

The assistant depends on an ingestion and retrieval pipeline before generation.
Documents must become searchable context before the language model can answer
questions from them. A question is first embedded and used to retrieve
supporting chunks from the caller's organization; only then is the model invoked,
conditioned on those chunks.

Why grounding is required

The language model has no knowledge of any particular organization's internal
documents. Asked directly, it would produce fluent text that is not derived from
any source — the failure mode that makes a general assistant unusable for
company knowledge. Supplying retrieved passages constrains the answer to
material the organization actually wrote and makes provenance reportable.

Context assembly

Retrieved chunks are ordered and concatenated into a bounded context. The bound
matters: a model has a finite context window, and filling it with marginally
relevant passages both costs computation and dilutes the signal from the
passages that answer the question. Retrieval quality therefore directly limits
answer quality, because a chunk that retrieval fails to surface cannot be used
no matter how capable the model is.

Tenancy in the assistant path

The assistant retrieves through the same organization-filtered path as search.
It does not receive a broader view of the corpus. Consequently an answer can only
be grounded in documents the asking user's organization owns.

Failure modes

Two failure modes are distinct and worth separating. Retrieval failure means the
answering passage was never surfaced, and no prompt change can fix it.
Generation failure means the passage was present but the model summarized it
poorly or overstated its certainty. Diagnosing the assistant therefore begins
with inspecting what retrieval returned, not with rewriting the prompt.
""",
    "Knowledge Retrieval Architecture": """
Knowledge Retrieval Architecture

Knowledge retrieval connects query embedding, vector similarity search, document
chunks, and organization filtering into a single retrieval flow. The
architecture's purpose is to turn a natural-language question into a ranked set
of passages drawn from one organization's documents.

Components of the flow

A query arrives from an authenticated caller. The caller's organization is
resolved from their user record. The query text is embedded by the embedding
service. A database query ranks that organization's chunks by cosine similarity
to the query vector and returns the top matches with their text, score, and
source document. Each component has one responsibility and can be replaced
without rewriting the others.

Answers come from stored chunks

Retrieval results are produced from stored document chunks rather than directly
querying the language model for company knowledge. This is the architectural
commitment that makes answers traceable: every returned passage exists in a
document the organization uploaded, and can be pointed at. A design that asked
the model for company facts would produce unverifiable output.

Chunk-level retrieval, document-level reasoning

Retrieval operates on chunks because chunks are what carry embeddings, but
consumers often reason about documents. Several chunks from one document may all
rank highly, so document-level views deduplicate while preserving order, keeping
each document at the rank of its best-matching chunk. Deduplicating this way
rather than by re-scoring keeps the document ordering consistent with the chunk
ordering that produced it.

Ranking strategies are pluggable

The flow's ranking step is deliberately replaceable. Pure semantic similarity,
lexical matching, weighted score fusion, reciprocal rank fusion, and a
reranking stage over a wider candidate pool all fit the same interface. Because
they are interchangeable, they can be compared on identical data.

Separating chunking effects from ranking effects

Two independent factors influence retrieval quality: how documents were divided
into chunks, and how candidate chunks were ranked. A measured improvement is
attributable only if one factor is held fixed while the other varies. Comparing
chunking configurations under an identical ranking strategy isolates the
chunking effect; comparing ranking strategies over an identical chunk set
isolates the ranking effect.
""",
    "API Security": """
API Security

Protected KnowledgeOS API endpoints require authenticated requests. JWT
authentication establishes the identity used for access control and
organization-aware retrieval. Security at the API boundary rests on three
mechanisms that apply together rather than on any one of them.

Layered mechanisms

API security combines authentication, authorization, and tenant-aware filtering
so protected knowledge operations remain scoped to the requesting user.
Authentication establishes who is calling. Authorization decides whether that
caller may perform the requested operation. Tenant filtering constrains which
documents the operation may touch. Removing any one layer breaks a different
guarantee: without authentication there is no identity to authorize, without
authorization every authenticated user is an administrator, and without tenant
filtering a permitted search ranges over other organizations' knowledge.

Request path

A request presenting no token, an expired token, or an invalid signature is
rejected before reaching knowledge logic. A request with a valid token proceeds
to permission evaluation for the specific operation. A permitted operation then
executes against a queryset already restricted to the caller's organization.

Server-side scope resolution

Scope is never taken from the request body. The organization used for retrieval
is read from the authenticated user, so a caller cannot broaden their access by
supplying a different organization identifier. This is the difference between a
tenant boundary and a convention that clients are expected to respect.

Error behavior

Failures are reported without leaking structure. An unauthorized request is not
told whether the resource it named exists, because existence can itself be
sensitive. Validation errors describe what was malformed about the request
without echoing back stored content.

Transport and storage assumptions

The model assumes transport encryption and that tokens are treated as
credentials by clients. Short token lifetimes limit exposure from a leaked
token, but they do not remove the client's obligation not to persist tokens
where other parties can read them.
""",
}


def get_source_text(title: str) -> str:
    """
    Return the normalized source text for ``title``.

    The literal above is indented for readability inside this module; callers
    receive the text with that formatting preserved verbatim so every
    configuration chunks byte-identical input.
    """
    return SOURCE_DOCUMENTS[title].strip()
