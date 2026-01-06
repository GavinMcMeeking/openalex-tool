"""
Configuration module for OpenAlex CLI tool.
Defines available fields, field mappings, and default field sets.
"""

# Core fields that are included by default
CORE_FIELDS = [
    "id",
    "title",
    "abstract",
    "authors",
    "publication_date",
    "doi",
    "type"
]

# Extended fields available for selection
EXTENDED_FIELDS = [
    "concepts",
    "keywords",
    "cited_by_count",
    "institutions",
    "sources",
    "publisher",
    "language",
    "is_oa",
    "open_access",
    "primary_location",
    "locations",
    "referenced_works",
    "related_works",
    "year",
    "created_date",
    "updated_date",
    "publication_year",
    "cited_by_api_url",
    "related_works_api_url"
]

# All available fields
ALL_FIELDS = CORE_FIELDS + EXTENDED_FIELDS

# Field aliases for user-friendly names
FIELD_ALIASES = {
    "author": "authors",
    "date": "publication_date",
    "pub_date": "publication_date",
    "citation_count": "cited_by_count",
    "citations": "cited_by_count",
    "institution": "institutions",
    "source": "sources",
    "journal": "sources",
    "venue": "sources",
    "open_access": "is_oa",
    "oa": "is_oa"
}

# Fields that need special handling in the formatter
NESTED_FIELDS = {
    "authors": "authorships",
    "institutions": "authorships",
    "concepts": "concepts",
    "keywords": "keywords",
    "sources": "primary_location",
    "publisher": "primary_location"
}


def resolve_field_name(field_name: str) -> str:
    """
    Resolve a field name, handling aliases.
    
    Args:
        field_name: User-provided field name (may be an alias)
        
    Returns:
        Resolved field name from ALL_FIELDS
    """
    field_name = field_name.lower().strip()
    
    # Check if it's an alias
    if field_name in FIELD_ALIASES:
        field_name = FIELD_ALIASES[field_name]
    
    # Validate it's a known field
    if field_name not in ALL_FIELDS:
        raise ValueError(f"Unknown field: {field_name}")
    
    return field_name


def get_default_fields() -> list:
    """Get the list of default fields to include."""
    return CORE_FIELDS.copy()


def validate_fields(field_names: list) -> list:
    """
    Validate and resolve a list of field names.
    
    Args:
        field_names: List of field names (may include aliases)
        
    Returns:
        List of validated, resolved field names
    """
    resolved = []
    for field in field_names:
        resolved.append(resolve_field_name(field))
    return resolved


def get_fields_to_select(include_fields: list = None, exclude_fields: list = None) -> list:
    """
    Determine which fields to select based on include/exclude logic.
    
    Args:
        include_fields: List of fields to include (if None, uses defaults)
        exclude_fields: List of fields to exclude (if None, excludes nothing)
        
    Returns:
        List of field names to select from API
    """
    if include_fields:
        # User specified fields to include
        fields = validate_fields(include_fields)
    else:
        # Use default fields
        fields = get_default_fields()
    
    if exclude_fields:
        # Remove excluded fields
        exclude = validate_fields(exclude_fields)
        fields = [f for f in fields if f not in exclude]
    
    return fields

