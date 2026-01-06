"""
Output formatter module.
Handles transformation of OpenAlex work objects and JSON output writing.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional


def extract_authors(authorships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract and flatten author information from authorships.
    
    Args:
        authorships: List of authorship objects from OpenAlex
        
    Returns:
        List of simplified author dictionaries
    """
    authors = []
    for authorship in authorships or []:
        author = authorship.get("author", {})
        if author:
            author_info = {
                "id": author.get("id", ""),
                "name": author.get("display_name", ""),
                "orcid": author.get("orcid", "")
            }
            # Add position if available
            if "author_position" in authorship:
                author_info["position"] = authorship["author_position"]
            authors.append(author_info)
    return authors


def extract_institutions(authorships: List[Dict[str, Any]]) -> List[str]:
    """
    Extract institution names from authorships.
    
    Args:
        authorships: List of authorship objects from OpenAlex
        
    Returns:
        List of institution display names
    """
    institutions = []
    seen = set()
    
    for authorship in authorships or []:
        for institution in authorship.get("institutions", []):
            inst_name = institution.get("display_name", "")
            if inst_name and inst_name not in seen:
                institutions.append(inst_name)
                seen.add(inst_name)
    
    return institutions


def extract_concepts(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract concept information.
    
    Args:
        concepts: List of concept objects from OpenAlex
        
    Returns:
        List of simplified concept dictionaries
    """
    result = []
    for concept in concepts or []:
        concept_info = {
            "id": concept.get("id", ""),
            "name": concept.get("display_name", ""),
            "score": concept.get("score", 0.0)
        }
        result.append(concept_info)
    return result


def extract_keywords(keywords: List[Dict[str, Any]]) -> List[str]:
    """
    Extract keyword strings.
    
    Args:
        keywords: List of keyword objects from OpenAlex
        
    Returns:
        List of keyword strings
    """
    return [kw.get("display_name", "") for kw in (keywords or []) if kw.get("display_name")]


def extract_source(primary_location: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract source/journal information from primary location.
    
    Args:
        primary_location: Primary location object from OpenAlex
        
    Returns:
        Simplified source dictionary or None
    """
    if not primary_location:
        return None
    
    source = primary_location.get("source", {})
    if not source:
        return None
    
    return {
        "id": source.get("id", ""),
        "name": source.get("display_name", ""),
        "issn": source.get("issn_l", "") or source.get("issn", ""),
        "type": source.get("type", "")
    }


def format_work(work: Dict[str, Any], selected_fields: List[str]) -> Dict[str, Any]:
    """
    Transform OpenAlex work object to simplified structure.
    
    Args:
        work: Raw work object from OpenAlex API
        selected_fields: List of fields to include in output
        
    Returns:
        Simplified work dictionary
    """
    formatted = {}
    
    # Handle each selected field
    for field in selected_fields:
        if field == "authors":
            formatted["authors"] = extract_authors(work.get("authorships", []))
        elif field == "institutions":
            formatted["institutions"] = extract_institutions(work.get("authorships", []))
        elif field == "concepts":
            formatted["concepts"] = extract_concepts(work.get("concepts", []))
        elif field == "keywords":
            formatted["keywords"] = extract_keywords(work.get("keywords", []))
        elif field == "sources":
            formatted["source"] = extract_source(work.get("primary_location", {}))
        elif field == "publisher":
            source = extract_source(work.get("primary_location", {}))
            if source:
                formatted["publisher"] = source.get("name", "")
        elif field == "abstract":
            # Abstract might be in abstract_inverted_index or just abstract
            abstract = work.get("abstract", "")
            if not abstract and "abstract_inverted_index" in work:
                # Simple reconstruction from inverted index (basic approach)
                abstract = work.get("abstract", "")
            formatted["abstract"] = abstract
        elif field in work:
            # Direct field mapping
            formatted[field] = work[field]
        else:
            # Field not found, set to None
            formatted[field] = None
    
    return formatted


def write_json(
    works: List[Dict[str, Any]],
    output_path: str,
    query_info: Optional[Dict[str, Any]] = None
) -> None:
    """
    Write works to JSON file with metadata.
    
    Args:
        works: List of formatted work objects
        output_path: Path to output JSON file
        query_info: Dictionary with query information (search terms, filters, etc.)
    """
    output = {
        "works": works,
        "metadata": {
            "total": len(works),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": query_info or {}
        }
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved {len(works)} works to {output_path}")

