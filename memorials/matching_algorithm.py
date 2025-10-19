# ============================================================================
# memorials/matching_algorithm.py - CREATE THIS NEW FILE
# ============================================================================

from django.db import models
from difflib import SequenceMatcher


def find_potential_matches(memorial, limit=5):
    """
    Enhanced AI-powered matching algorithm
    Returns list of dicts with memorial, score, and reasons
    """
    from memorials.models import Memorial, SmartMatchSuggestion, FamilyRelationship
    
    potential_matches = []
    
    # Get all other approved memorials
    other_memorials = Memorial.objects.filter(
        approved=True
    ).exclude(
        id=memorial.id
    ).exclude(
        created_by=memorial.created_by
    )
    
    # Check existing relationships
    existing_relationships = set()
    for rel in FamilyRelationship.objects.filter(
        models.Q(person_a=memorial) | models.Q(person_b=memorial)
    ).values_list('person_a_id', 'person_b_id'):
        existing_relationships.add(rel[0])
        existing_relationships.add(rel[1])
    
    # Also exclude already suggested matches
    existing_suggestions = set(
        SmartMatchSuggestion.objects.filter(
            my_memorial=memorial
        ).values_list('suggested_memorial_id', flat=True)
    )
    
    other_memorials = other_memorials.exclude(
        id__in=existing_relationships | existing_suggestions
    )
    
    for other in other_memorials:
        score = 0
        reasons = []
        
        # 1. Name similarity (50 points max) - PRIMARY SIGNAL
        name_score = calculate_advanced_name_similarity(
            memorial.full_name,
            other.full_name
        )
        if name_score > 0.3:
            score += int(name_score * 50)
            if name_score > 0.9:
                reasons.append(f"🎯 Highly similar names ({int(name_score * 100)}%)")
            elif name_score > 0.7:
                reasons.append(f"Similar names ({int(name_score * 100)}%)")
            else:
                reasons.append(f"Partial name match ({int(name_score * 100)}%)")
        
        # 2. Last name matching (25 points) - HIGH CONFIDENCE
        last_name_bonus = calculate_last_name_bonus(
            memorial.full_name,
            other.full_name
        )
        if last_name_bonus > 0:
            score += last_name_bonus
            reasons.append("🏠 Same family surname")
        
        # 3. Geographic proximity (20 points)
        geo_score = calculate_geographic_score(memorial, other)
        if geo_score > 0:
            score += geo_score
            if memorial.country == other.country:
                reasons.append(f"🌍 Both from {memorial.country.name}")
        
        # 4. Age proximity (25 points) - GENERATIONAL PATTERNS
        if memorial.dob and other.dob:
            age_score = calculate_age_proximity_score(memorial.dob, other.dob)
            if age_score > 0:
                score += age_score
                year_diff = abs(memorial.dob.year - other.dob.year)
                if year_diff <= 2:
                    reasons.append("👥 Born in same year")
                elif year_diff <= 5:
                    reasons.append(f"👥 Within {year_diff} years of age")
                elif year_diff <= 15:
                    reasons.append("👨‍👩‍👧 Likely parent-child generation")
        
        # 5. Timeline overlap (15 points)
        if memorial.dob and memorial.dod and other.dob and other.dod:
            timeline_score = calculate_timeline_overlap_score(
                memorial.dob, memorial.dod, other.dob, other.dod
            )
            if timeline_score > 0:
                score += timeline_score
                reasons.append("📅 Lived during overlapping periods")
        
        # 6. Biography similarity (15 points)
        if hasattr(memorial, 'bio') and hasattr(other, 'bio') and memorial.bio and other.bio:
            bio_score = calculate_bio_similarity_score(memorial.bio, other.bio)
            if bio_score > 0:
                score += bio_score
                reasons.append("📖 Similar life stories")
        
        # Only include matches above threshold
        if score >= 35:
            potential_matches.append({
                'memorial': other,
                'score': min(score, 100),  # Cap at 100
                'reasons': reasons
            })
    
    # Sort by score and return top matches
    potential_matches.sort(key=lambda x: x['score'], reverse=True)
    return potential_matches[:limit]


def calculate_advanced_name_similarity(name1, name2):
    """Advanced name similarity with first/last name weighting"""
    name1 = name1.lower().strip()
    name2 = name2.lower().strip()
    
    # Direct comparison
    basic_ratio = SequenceMatcher(None, name1, name2).ratio()
    
    # Compare first and last names separately
    parts1 = name1.split()
    parts2 = name2.split()
    
    if len(parts1) > 0 and len(parts2) > 0:
        first_match = SequenceMatcher(None, parts1[0], parts2[0]).ratio()
        last_match = SequenceMatcher(None, parts1[-1], parts2[-1]).ratio()
        
        # Last name weighted more heavily (70% weight)
        parts_ratio = (first_match * 0.3 + last_match * 0.7)
    else:
        parts_ratio = basic_ratio
    
    return max(basic_ratio, parts_ratio)


def calculate_last_name_bonus(name1, name2):
    """Exact last name match bonus"""
    last1 = name1.strip().split()[-1].lower()
    last2 = name2.strip().split()[-1].lower()
    
    if last1 == last2 and len(last1) > 2:
        return 25
    return 0


def calculate_geographic_score(memorial1, memorial2):
    """Geographic proximity scoring"""
    score = 0
    
    if memorial1.country == memorial2.country:
        score += 15
        
        if hasattr(memorial1, 'state') and hasattr(memorial2, 'state'):
            if memorial1.state and memorial2.state and memorial1.state == memorial2.state:
                score += 5
    
    return score


def calculate_age_proximity_score(dob1, dob2):
    """Calculate age proximity scoring"""
    year_diff = abs(dob1.year - dob2.year)
    
    if year_diff == 0:
        return 25
    elif year_diff <= 2:
        return 22
    elif year_diff <= 5:
        return 18
    elif year_diff <= 15:
        return 12
    elif year_diff <= 30:
        return 6
    
    return 0


def calculate_timeline_overlap_score(dob1, dod1, dob2, dod2):
    """Score based on timeline overlap"""
    if dob1 <= dod2 and dob2 <= dod1:
        overlap_start = max(dob1, dob2)
        overlap_end = min(dod1, dod2)
        overlap_years = (overlap_end - overlap_start).days / 365.25
        
        if overlap_years > 40:
            return 15
        elif overlap_years > 20:
            return 12
        elif overlap_years > 5:
            return 8
        else:
            return 3
    
    return 0


def calculate_bio_similarity_score(bio1, bio2):
    """Compare biography text similarity"""
    if not bio1 or not bio2:
        return 0
    
    bio1_lower = bio1.lower()
    bio2_lower = bio2.lower()
    
    keywords1 = set(bio1_lower.split())
    keywords2 = set(bio2_lower.split())
    
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'was', 'were', 'is', 'are', 'be', 'been', 'being', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
    }
    
    keywords1 = keywords1 - common_words
    keywords2 = keywords2 - common_words
    
    if not keywords1 or not keywords2:
        return 0
    
    # Jaccard similarity
    intersection = len(keywords1 & keywords2)
    union = len(keywords1 | keywords2)
    similarity = intersection / union if union > 0 else 0
    
    if similarity > 0.3:
        return 15
    elif similarity > 0.15:
        return 8
    
    return 0