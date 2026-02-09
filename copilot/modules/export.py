import csv
from typing import List, Union
from pathlib import Path
from datetime import datetime

from ..models.schemas import Lead, ValidationReport, ScrapedPost, PainScore
from ..providers.storage.base import StorageProvider

class ExportModule:
    def __init__(self, storage: StorageProvider):
        self.storage = storage

    def export_leads_to_csv(self, file_path: Path):
        leads = self.storage.get_leads(limit=None) # Fetch all leads
        if not leads:
            return 0
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = Lead.model_fields.keys() # Use pydantic model_fields for headers
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for lead in leads:
                row = lead.model_dump()
                # Flatten verified_profiles for CSV
                if 'verified_profiles' in row and isinstance(row['verified_profiles'], dict):
                    row['verified_profiles'] = '; '.join([f"{k}: {v}" for k, v in row['verified_profiles'].items()])
                writer.writerow(row)
        return len(leads)

    def export_leads_to_hubspot_csv(self, file_path: Path):
        """Export leads in a format compatible with HubSpot Contact Import."""
        leads = self.storage.get_leads(limit=None)
        if not leads:
            return 0

        # HubSpot standard headers for contacts
        # Mapping: author -> Last Name (or First Name if split), contact_url -> Website URL, etc.
        headers = [
            "First Name", 
            "Last Name", 
            "Email Address", 
            "Website URL", 
            "Job Title", 
            "Company Name", 
            "Lead Status", 
            "Intent Score",
            "Source Post",
            "Platform",
            "LinkedIn Profile"
        ]

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for lead in leads:
                # Simple split for name if possible, else use as Last Name
                name_parts = lead.author.split(' ', 1)
                first_name = name_parts[0] if len(name_parts) > 1 else ""
                last_name = name_parts[1] if len(name_parts) > 1 else lead.author
                
                linkedin = lead.verified_profiles.get('linkedin', '')
                
                writer.writerow({
                    "First Name": first_name,
                    "Last Name": last_name,
                    "Email Address": "", # We don't have emails yet
                    "Website URL": lead.contact_url,
                    "Job Title": "",
                    "Company Name": "",
                    "Lead Status": "NEW",
                    "Intent Score": f"{lead.intent_score:.2f}",
                    "Source Post": lead.post_id,
                    "Platform": lead.source,
                    "LinkedIn Profile": linkedin
                })
        return len(leads)

    def export_leads_to_salesforce_csv(self, file_path: Path):
        """Export leads in a format compatible with Salesforce Lead Import."""
        leads = self.storage.get_leads(limit=None)
        if not leads:
            return 0

        # Salesforce standard headers for leads
        headers = [
            "FirstName",
            "LastName",
            "Company",
            "Email",
            "Website",
            "Status",
            "LeadSource",
            "Rating",
            "Description"
        ]

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for lead in leads:
                name_parts = lead.author.split(' ', 1)
                first_name = name_parts[0] if len(name_parts) > 1 else ""
                last_name = name_parts[1] if len(name_parts) > 1 else lead.author
                
                # Salesforce Ratings are usually Cold, Warm, Hot
                rating = "Hot" if lead.intent_score > 0.8 else ("Warm" if lead.intent_score > 0.5 else "Cold")
                
                writer.writerow({
                    "FirstName": first_name,
                    "LastName": last_name,
                    "Company": "[Unknown]", # Required by SF often
                    "Email": "",
                    "Website": lead.contact_url,
                    "Status": "Open - Not Contacted",
                    "LeadSource": lead.source.capitalize(),
                    "Rating": rating,
                    "Description": f"Intent Score: {lead.intent_score:.2f}. Snippet: {lead.content_snippet}"
                })
        return len(leads)

    def export_reports_to_csv(self, file_path: Path):
        reports = self.storage.get_reports(limit=None) # Fetch all reports
        if not reports:
            return 0
            
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ValidationReport.model_fields.keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for report in reports:
                # Flatten complex fields for CSV
                report_dict = report.model_dump()
                report_dict['competitors'] = '; '.join([f"{c.get('Name', '')}: {c.get('URL', '')}" for c in report_dict.get('competitors', [])])
                report_dict['swot_analysis'] = '; '.join([f"{k}: {', '.join(v)}" for k, v in report_dict.get('swot_analysis', {}).items()])
                report_dict['next_steps'] = '; '.join(report_dict.get('next_steps', []))
                writer.writerow(report_dict)
        return len(reports)

    def export_leads_to_md(self, file_path: Path):
        leads = self.storage.get_leads(limit=None)
        if not leads:
            return 0

        with open(file_path, 'w', encoding='utf-8') as mdfile:
            mdfile.write("# Potential Customer Leads\n\n")
            mdfile.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for lead in leads:
                mdfile.write(f"## Lead: {lead.author} (Score: {lead.intent_score:.2f})\n")
                mdfile.write(f"- **Needs Summary:** {lead.content_snippet}\n")
                mdfile.write(f"- **Contact URL:** [{lead.contact_url}]({lead.contact_url})\n")
                mdfile.write(f"- **Status:** {lead.status}\n")
                mdfile.write(f"- **Post ID:** {lead.post_id}\n")
                mdfile.write(f"- **Created At:** {lead.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                mdfile.write("\n---\n\n")
        return len(leads)

    def export_reports_to_md(self, file_path: Path):
        reports = self.storage.get_reports(limit=None)
        if not reports:
            return 0

        with open(file_path, 'w', encoding='utf-8') as mdfile:
            mdfile.write("# Validation Reports\n\n")
            mdfile.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for report in reports:
                mdfile.write(f"## Report for Post ID: {report.post_id}\n")
                mdfile.write(f"### Idea Summary\n{report.idea_summary}\n\n")
                mdfile.write(f"### Market Size Estimate\n{report.market_size_estimate}\n\n")
                
                if report.competitors:
                    mdfile.write("### Competitors\n")
                    for comp in report.competitors:
                        mdfile.write(f"- **{comp.get('Name', 'N/A')}**: [{comp.get('URL', 'N/A')}]({comp.get('URL', '#')}) - {comp.get('Description', 'N/A')}\n")
                    mdfile.write("\n")

                if report.swot_analysis:
                    mdfile.write("### SWOT Analysis\n")
                    for category, items in report.swot_analysis.items():
                        mdfile.write(f"**{category.capitalize()}:**\n")
                        for item in items:
                            mdfile.write(f"  - {item}\n")
                    mdfile.write("\n")

                mdfile.write(f"### Validation Verdict\n{report.validation_verdict}\n\n")
                
                if report.next_steps:
                    mdfile.write("### Next Steps\n")
                    for step in report.next_steps:
                        mdfile.write(f"- {step}\n")
                    mdfile.write("\n")
                
                mdfile.write(f"Generated At: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                mdfile.write("\n---\n\n")
        return len(reports)