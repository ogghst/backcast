#!/usr/bin/env python3
"""
Script to generate a project template from a quotation file.
Maps categories to WBEs and items' cost fields to cost elements.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta

# Mapping of cost field names to department codes and names
COST_FIELD_TO_DEPARTMENT = {
    "utm_robot": ("MECH", "Mechanical Engineering"),
    "utm_lgv": ("MECH", "Mechanical Engineering"),
    "utm_intra": ("MECH", "Mechanical Engineering"),
    "utm_layout": ("MECH", "Mechanical Engineering"),
    "site": ("MECH", "Mechanical Engineering"),
    "install": ("MECH", "Mechanical Engineering"),
    "ute": ("ELEC", "Electrical Engineering"),
    "sw_pc": ("SW", "Software Development"),
    "sw_plc": ("SW", "Software Development"),
    "sw_lgv": ("SW", "Software Development"),
    "mtg_mec": ("ASM", "Assembly"),
    "mtg_mec_intra": ("ASM", "Assembly"),
    "cab_ele": ("ASM", "Assembly"),
    "cab_ele_intra": ("ASM", "Assembly"),
    "coll_ba": ("COM", "Commissioning"),
    "coll_pc": ("COM", "Commissioning"),
    "coll_plc": ("COM", "Commissioning"),
    "coll_lgv": ("COM", "Commissioning"),
    "pm_cost": ("PM", "Project Management"),
    "document": ("SUPPORT", "Support & Documentation"),
    "av_pc": ("SUPPORT", "Support & Documentation"),
    "av_plc": ("SUPPORT", "Support & Documentation"),
    "av_lgv": ("SUPPORT", "Support & Documentation"),
    "mat": ("MAT", "Materials"),
    "imballo": ("MAT", "Materials"),
    "stoccaggio": ("MAT", "Materials"),
    "trasporto": ("MAT", "Materials"),
    "spese_pm": ("OTHER", "Other"),
    "spese_field": ("OTHER", "Other"),
    "spese_varie": ("OTHER", "Other"),
    "after_sales": ("OTHER", "Other"),
}

# Fields to exclude (hour fields and other non-cost fields)
EXCLUDE_FIELDS = {
    "utm_robot_h",
    "utm_lgv_h",
    "utm_intra_h",
    "utm_layout_h",
    "ute_h",
    "ba",
    "ba_h",
    "sw_pc_h",
    "sw_plc_h",
    "sw_lgv_h",
    "mtg_mec_h",
    "mtg_mec_intra_h",
    "cab_ele_h",
    "cab_ele_intra_h",
    "coll_ba_h",
    "coll_pc_h",
    "coll_plc_h",
    "coll_lgv_h",
    "pm_h",
    "document_h",
    "av_pc_h",
    "av_plc_h",
    "av_lgv_h",
    "provvigioni_italia",
    "provvigioni_estero",
    "tesoretto",
    "montaggio_bema_mbe_us",
    "total",
    "wbs",
    "position",
    "code",
    "cod_listino",
    "description",
    "quantity",
    "pricelist_unit_price",
    "pricelist_total_price",
    "unit_cost",
    "total_cost",
    "internal_code",
    "priority_order",
    "priority",
    "line_number",
}

# Mapping of cost field to cost element type code
COST_FIELD_TO_TYPE_CODE = {
    "utm_robot": "utm_robot",
    "utm_lgv": "utm_lgv",
    "utm_intra": "utm_intra",
    "utm_layout": "utm_layout",
    "site": "site",
    "install": "install",
    "ute": "ute",
    "sw_pc": "sw_pc",
    "sw_plc": "sw_plc",
    "sw_lgv": "sw_lgv",
    "mtg_mec": "mtg_mec",
    "mtg_mec_intra": "mtg_mec",
    "cab_ele": "cab_ele",
    "cab_ele_intra": "cab_ele",
    "coll_ba": "coll_ba",
    "coll_pc": "coll_pc",
    "coll_plc": "coll_plc",
    "coll_lgv": "coll_lgv",
    "pm_cost": "pm_cost",
    "document": "document",
    "av_pc": "av_pc",
    "av_plc": "av_pc",
    "av_lgv": "av_pc",
    "mat": "mat",
    "imballo": "imballo",
    "stoccaggio": "stoccaggio",
    "trasporto": "trasporto",
    "spese_pm": "spese_pm",
    "spese_field": "spese_field",
    "spese_varie": "spese_field",
    "after_sales": "spese_field",
}


def extract_cost_elements_from_item(item):
    """Extract cost elements from a single item - one cost element per cost field type."""
    result = []

    # Iterate through all fields in the item
    for field_name, value in item.items():
        # Skip excluded fields
        if field_name in EXCLUDE_FIELDS:
            continue

        # Check if this field maps to a department
        if field_name in COST_FIELD_TO_DEPARTMENT:
            dept_code, dept_name = COST_FIELD_TO_DEPARTMENT[field_name]
            type_code = COST_FIELD_TO_TYPE_CODE.get(field_name, field_name)

            # Only process non-zero values
            if value and isinstance(value, (int, float)) and value != 0.0:
                result.append(
                    {
                        "department_code": dept_code,
                        "department_name": dept_name,
                        "cost_element_type_code": type_code,
                        "cost_element_type_id": "REPLACE_WITH_VALID_COST_ELEMENT_TYPE_UUID",
                        "budget_bac": round(float(value), 2),
                        "revenue_plan": round(
                            float(value) * 1.2, 2
                        ),  # Default 20% margin
                        "status": "planned",
                    }
                )

    return result


def generate_serial_number(category_name, index):
    """Generate a serial number from category name."""
    # Take first 3 letters of each word, or use index
    words = category_name.split()
    if words:
        prefix = "".join([w[:3].upper() for w in words[:2]])[:6]
        return f"{prefix}-{index:03d}"
    return f"WBE-{index:03d}"


def transform_quotation_to_template(quotation_path, output_path=None):
    """Transform quotation file to project template format."""

    # Read quotation file
    with open(quotation_path, "r", encoding="utf-8") as f:
        quotation = json.load(f)

    # Extract project info
    project_info = quotation.get("project", {})

    # Calculate dates (defaults if not available)
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")

    # Build template
    template = {
        "project": {
            "project_name": project_info.get("id", "New Project"),
            "customer_name": project_info.get("customer", ""),
            "contract_value": 0.0,  # Will be calculated from categories
            "project_code": project_info.get("id", "PROJ-NEW-001"),
            "pricelist_code": project_info.get("listino", "LISTINO 118"),
            "start_date": start_date,
            "planned_completion_date": end_date,
            "project_manager_id": "REPLACE_WITH_VALID_USER_UUID",
            "status": "active",
            "notes": f"Generated from quotation: {project_info.get('id', 'N/A')}",
        },
        "wbes": [],
    }

    # Process product groups and categories
    product_groups = quotation.get("product_groups", [])
    wbe_index = 1
    total_revenue = 0.0

    for group in product_groups:
        categories = group.get("categories", [])

        for category in categories:
            # Skip categories with no items or no meaningful data
            items = category.get("items", [])
            if not items:
                continue

            # Aggregate cost elements from all items in this category
            # Aggregate by department and cost element type (e.g., utm_robot, ute, sw_pc)
            all_cost_elements = []
            category_cost_elements = defaultdict(
                float
            )  # key: (dept_code, type_code), value: sum

            for item in items:
                item_cost_elements = extract_cost_elements_from_item(item)
                # Aggregate by department and type
                for ce in item_cost_elements:
                    dept_code = ce["department_code"]
                    type_code = ce.get("cost_element_type_code", "unknown")
                    key = (dept_code, type_code)
                    category_cost_elements[key] = (
                        category_cost_elements.get(key, 0) + ce["budget_bac"]
                    )

            # Create cost elements (one per department-type combination)
            for (dept_code, type_code), budget_bac in category_cost_elements.items():
                # Find department name from mapping
                dept_name = "Unknown Department"
                for field, (code, name) in COST_FIELD_TO_DEPARTMENT.items():
                    if code == dept_code:
                        dept_name = name
                        break

                all_cost_elements.append(
                    {
                        "department_code": dept_code,
                        "department_name": dept_name,
                        "cost_element_type_id": "REPLACE_WITH_VALID_COST_ELEMENT_TYPE_UUID",
                        "budget_bac": round(budget_bac, 2),
                        "revenue_plan": round(
                            budget_bac * 1.2, 2
                        ),  # Default 20% margin
                        "status": "planned",
                        "notes": f"Cost element for {dept_name} (type: {type_code}) aggregated from category items",
                    }
                )

            # Skip if no cost elements found
            if not all_cost_elements:
                continue

            # Calculate revenue allocation for this WBE
            revenue_allocation = category.get("offer_price", 0.0)
            if revenue_allocation == 0.0:
                # Use pricelist_subtotal if offer_price is 0
                revenue_allocation = category.get("pricelist_subtotal", 0.0)

            # If still 0, calculate from cost elements
            if revenue_allocation == 0.0:
                revenue_allocation = sum(ce["revenue_plan"] for ce in all_cost_elements)

            total_revenue += revenue_allocation

            # Create WBE
            category_name = category.get("category_name", f"Category {wbe_index}")
            serial_number = category.get("wbe", "") or generate_serial_number(
                category_name, wbe_index
            )

            wbe = {
                "wbe": {
                    "machine_type": category_name,
                    "serial_number": serial_number,
                    "contracted_delivery_date": end_date,
                    "revenue_allocation": round(revenue_allocation, 2),
                    "status": "designing",
                    "notes": f"WBE generated from category: {category_name}",
                },
                "cost_elements": all_cost_elements,
            }

            template["wbes"].append(wbe)
            wbe_index += 1

    # Update contract value
    if total_revenue > 0:
        template["project"]["contract_value"] = round(total_revenue, 2)

    # Write output
    if output_path is None:
        output_path = quotation_path.replace(".json", "_template.json")
        # If file has spaces or special chars, handle it
        if " " in output_path:
            output_path = (
                output_path.replace(" copy", "").replace(" ", "_") + "_template.json"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print(f"✓ Generated project template: {output_path}")
    print(f"  - Project: {template['project']['project_name']}")
    print(f"  - WBEs: {len(template['wbes'])}")
    print(f"  - Total Contract Value: {template['project']['contract_value']:,.2f}")

    return template


if __name__ == "__main__":
    import sys

    quotation_path = (
        sys.argv[1] if len(sys.argv) > 1 else "resources/quotation_ap_direct copy.json"
    )
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    transform_quotation_to_template(quotation_path, output_path)
