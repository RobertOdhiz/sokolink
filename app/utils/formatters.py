"""
Utility functions for formatting data and messages.
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from app.models.response_models import ComplianceStep, ComplianceResponse

logger = structlog.get_logger()


def format_currency(amount: int, currency: str = "KES") -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Amount in cents/smallest unit
        currency: Currency code
        
    Returns:
        str: Formatted currency string
    """
    if currency == "KES":
        return f"KSh {amount:,}"
    else:
        return f"{currency} {amount:,}"


def format_duration(days: int) -> str:
    """
    Format duration in days to human-readable string.
    
    Args:
        days: Number of days
        
    Returns:
        str: Formatted duration string
    """
    if days == 1:
        return "1 day"
    elif days < 7:
        return f"{days} days"
    elif days < 30:
        weeks = days // 7
        remaining_days = days % 7
        if remaining_days == 0:
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            return f"{weeks} week{'s' if weeks > 1 else ''} and {remaining_days} day{'s' if remaining_days > 1 else ''}"
    elif days < 365:
        months = days // 30
        remaining_days = days % 30
        if remaining_days == 0:
            return f"{months} month{'s' if months > 1 else ''}"
        else:
            return f"{months} month{'s' if months > 1 else ''} and {remaining_days} day{'s' if remaining_days > 1 else ''}"
    else:
        years = days // 365
        remaining_days = days % 365
        if remaining_days == 0:
            return f"{years} year{'s' if years > 1 else ''}"
        else:
            return f"{years} year{'s' if years > 1 else ''} and {remaining_days} day{'s' if remaining_days > 1 else ''}"


def format_whatsapp_message(compliance_response: ComplianceResponse) -> str:
    """
    Format compliance response for WhatsApp message.
    
    Args:
        compliance_response: Compliance response data
        
    Returns:
        str: Formatted WhatsApp message
    """
    message_parts = []
    
    # Header
    message_parts.append("🏢 *Sokolink Compliance Advisor*")
    message_parts.append("")
    
    # Business info if available
    if compliance_response.business_type:
        message_parts.append(f"📋 *Business Type:* {compliance_response.business_type}")
    if compliance_response.business_scale:
        message_parts.append(f"📏 *Scale:* {compliance_response.business_scale}")
    if compliance_response.location:
        message_parts.append(f"📍 *Location:* {compliance_response.location}")
    
    message_parts.append("")
    
    # Summary
    message_parts.append("📊 *Compliance Summary:*")
    message_parts.append(f"💰 Total Cost: {format_currency(compliance_response.total_estimated_cost)}")
    message_parts.append(f"⏱️ Total Time: {format_duration(compliance_response.total_timeline_days)}")
    message_parts.append("")
    
    # Steps
    message_parts.append("📝 *Required Steps:*")
    for i, step in enumerate(compliance_response.compliance_steps, 1):
        message_parts.append(f"")
        message_parts.append(f"*{i}. {step.title}*")
        message_parts.append(f"   {step.description}")
        message_parts.append(f"   💰 Cost: {format_currency(step.cost)}")
        message_parts.append(f"   ⏱️ Time: {format_duration(step.timeline_days)}")
        message_parts.append(f"   🏛️ Authority: {step.authority}")
        
        if step.documents_required:
            docs = ", ".join(step.documents_required)
            message_parts.append(f"   📄 Documents: {docs}")
        
        if step.contact_info:
            message_parts.append(f"   📞 Contact: {step.contact_info}")
    
    # Additional notes
    if compliance_response.additional_notes:
        message_parts.append("")
        message_parts.append("💡 *Additional Notes:*")
        message_parts.append(compliance_response.additional_notes)
    
    # Footer
    message_parts.append("")
    message_parts.append("Need more help? Reply with your questions!")
    message_parts.append("")
    message_parts.append("_Powered by Sokolink & IBM Watsonx_")
    
    return "\n".join(message_parts)


def format_whatsapp_message_short(compliance_response: ComplianceResponse) -> str:
    """
    Format compliance response for WhatsApp message (short version).
    
    Args:
        compliance_response: Compliance response data
        
    Returns:
        str: Formatted WhatsApp message (short)
    """
    message_parts = []
    
    # Header
    message_parts.append("🏢 *Sokolink Compliance Advisor*")
    message_parts.append("")
    
    # Summary
    message_parts.append("📊 *Quick Summary:*")
    message_parts.append(f"💰 Total Cost: {format_currency(compliance_response.total_estimated_cost)}")
    message_parts.append(f"⏱️ Total Time: {format_duration(compliance_response.total_timeline_days)}")
    message_parts.append(f"📝 Steps Required: {len(compliance_response.compliance_steps)}")
    message_parts.append("")
    
    # Top 3 steps
    message_parts.append("🎯 *Key Steps:*")
    for i, step in enumerate(compliance_response.compliance_steps[:3], 1):
        message_parts.append(f"{i}. {step.title} - {format_currency(step.cost)}")
    
    if len(compliance_response.compliance_steps) > 3:
        message_parts.append(f"... and {len(compliance_response.compliance_steps) - 3} more steps")
    
    message_parts.append("")
    message_parts.append("Reply 'DETAILS' for full step-by-step guide!")
    
    return "\n".join(message_parts)


def split_long_message(message: str, max_length: int = 4096) -> List[str]:
    """
    Split long message into chunks for WhatsApp.
    
    Args:
        message: Message to split
        max_length: Maximum length per chunk
        
    Returns:
        List[str]: List of message chunks
    """
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs first
    paragraphs = message.split("\n\n")
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                # Paragraph is too long, split by sentences
                sentences = paragraph.split("\n")
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_length:
                        if current_chunk:
                            current_chunk += "\n" + sentence
                        else:
                            current_chunk = sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = sentence
                        else:
                            # Sentence is too long, force split
                            while len(sentence) > max_length:
                                chunks.append(sentence[:max_length])
                                sentence = sentence[max_length:]
                            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def format_error_message(error_code: str, error_message: str) -> str:
    """
    Format error message for WhatsApp.
    
    Args:
        error_code: Error code
        error_message: Error message
        
    Returns:
        str: Formatted error message
    """
    return f"❌ *Error {error_code}*\n\n{error_message}\n\nPlease try again or contact support if the issue persists."


def format_welcome_message() -> str:
    """
    Format welcome message for new users.
    
    Returns:
        str: Welcome message
    """
    return """🏢 *Welcome to Sokolink Compliance Advisor!*

I'm here to help you navigate Kenya's business compliance requirements.

📝 *How to get started:*
1. Tell me about your business type
2. Share your business location
3. Describe what you want to do

I'll provide you with:
✅ Step-by-step compliance guide
✅ Cost estimates
✅ Timeline information
✅ Contact details for authorities

*Example:* "I want to start a small restaurant in Nairobi"

What business are you planning to start?"""


def format_help_message() -> str:
    """
    Format help message for users.
    
    Returns:
        str: Help message
    """
    return """🆘 *Sokolink Help*

*Available Commands:*
• Send any message about your business
• Type 'DETAILS' for full compliance guide
• Type 'SUMMARY' for quick overview
• Type 'HELP' for this message
• Type 'START' to begin new session

*Tips:*
• Be specific about your business type
• Include your location (county/town)
• Mention your business scale (small/medium/large)

*Example Messages:*
• "I want to start a small shop in Mombasa"
• "How do I register a restaurant business?"
• "What permits do I need for a salon?"

Need more help? Just ask! 😊"""


def format_business_type_suggestion(business_type: str) -> str:
    """
    Format business type suggestion message.
    
    Args:
        business_type: Detected business type
        
    Returns:
        str: Suggestion message
    """
    return f"""🎯 *I think you're starting a {business_type} business.*

Is this correct? If yes, I'll provide specific compliance requirements.

If not, please provide more details about your business type.

*Common business types:*
• Restaurant/Food business
• Retail shop
• Salon/Beauty services
• Construction
• Transport/Logistics
• Manufacturing
• Professional services

What type of business are you planning?"""


def clean_phone_number(phone_number: str) -> str:
    """
    Clean and normalize phone number for display.
    
    Args:
        phone_number: Raw phone number
        
    Returns:
        str: Cleaned phone number
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone_number)
    
    # Handle Kenyan numbers
    if digits.startswith('254'):
        return f"+{digits}"
    elif digits.startswith('0') and len(digits) == 10:
        return f"+254{digits[1:]}"
    elif len(digits) == 9:
        return f"+254{digits}"
    else:
        return f"+{digits}"


def format_authority_contact(authority: str, contact_info: str) -> str:
    """
    Format authority contact information.
    
    Args:
        authority: Authority name
        contact_info: Contact information
        
    Returns:
        str: Formatted contact info
    """
    if not contact_info:
        return f"Contact {authority} directly"
    
    # Check if it's an email
    if '@' in contact_info:
        return f"📧 Email: {contact_info}"
    
    # Check if it's a phone number
    if re.match(r'^[\+]?[0-9\s\-\(\)]+$', contact_info):
        return f"📞 Phone: {contact_info}"
    
    # Check if it's a website
    if contact_info.startswith(('http://', 'https://', 'www.')):
        return f"🌐 Website: {contact_info}"
    
    # Default format
    return f"📞 Contact: {contact_info}"


def format_documents_list(documents: List[str]) -> str:
    """
    Format list of required documents.
    
    Args:
        documents: List of document names
        
    Returns:
        str: Formatted documents list
    """
    if not documents:
        return "No specific documents required"
    
    if len(documents) == 1:
        return f"📄 Required: {documents[0]}"
    
    formatted_docs = []
    for i, doc in enumerate(documents, 1):
        formatted_docs.append(f"{i}. {doc}")
    
    return "📄 Required Documents:\n" + "\n".join(formatted_docs)


def format_timeline_summary(steps: List[ComplianceStep]) -> str:
    """
    Format timeline summary for compliance steps.
    
    Args:
        steps: List of compliance steps
        
    Returns:
        str: Formatted timeline summary
    """
    if not steps:
        return "No timeline information available"
    
    # Group steps by timeline
    timeline_groups = {}
    for step in steps:
        timeline_key = f"{step.timeline_days} days"
        if timeline_key not in timeline_groups:
            timeline_groups[timeline_key] = []
        timeline_groups[timeline_key].append(step.title)
    
    summary_parts = ["⏱️ *Timeline Summary:*"]
    
    for timeline, step_titles in sorted(timeline_groups.items()):
        summary_parts.append(f"• {timeline}: {', '.join(step_titles)}")
    
    return "\n".join(summary_parts)
