#!/usr/bin/env python3
"""
XML Linter for Odoo Views - Detects common view errors
Specifically designed to catch Odoo 18.0 breaking changes and bad patterns.
"""

import sys
import re
import argparse
from pathlib import Path
from typing import List, Tuple
from lxml import etree


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


class ViewLintError:
    """Represents a linting error in a view file"""
    
    def __init__(self, file_path: Path, line: int, column: int, error_code: str, 
                 message: str, severity: str = "ERROR"):
        self.file_path = file_path
        self.line = line
        self.column = column
        self.error_code = error_code
        self.message = message
        self.severity = severity
    
    def __str__(self):
        color = Colors.RED if self.severity == "ERROR" else Colors.YELLOW
        return (
            f"{color}{self.file_path}:{self.line}:{self.column}: "
            f"{self.severity} [{self.error_code}]{Colors.NC}\n"
            f"  {self.message}"
        )


class OdooViewLinter:
    """Linter for Odoo XML view files"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[ViewLintError] = []
        self.checked_files = 0
    
    def check_file(self, file_path: Path):
        """Check a single XML file for view errors"""
        if self.verbose:
            print(f"{Colors.BLUE}Checking: {file_path}{Colors.NC}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse XML
            try:
                tree = etree.fromstring(content.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                self.errors.append(ViewLintError(
                    file_path, e.lineno, 0, "XML001",
                    f"XML Syntax Error: {e.msg}"
                ))
                return
            
            # Run checks
            self._check_deprecated_tree_tag(file_path, content)
            self._check_deprecated_attrs(file_path, content)
            self._check_column_invisible_expressions(file_path, content)
            self._check_ref_in_context(file_path, content)
            self._check_view_architecture(file_path, tree)
            
            self.checked_files += 1
            
        except Exception as e:
            self.errors.append(ViewLintError(
                file_path, 0, 0, "XML000",
                f"Failed to read file: {str(e)}"
            ))
    
    def _check_deprecated_tree_tag(self, file_path: Path, content: str):
        """ODO18-001: Check for deprecated <tree> tag (should use <list>)"""
        pattern = r'<tree[>\s]'
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            self.errors.append(ViewLintError(
                file_path, line_num, match.start(), "ODO18-001",
                "Deprecated <tree> tag found. Use <list> instead in Odoo 18.0+",
                severity="ERROR"
            ))
    
    def _check_deprecated_attrs(self, file_path: Path, content: str):
        """ODO18-002: Check for deprecated attrs attribute"""
        pattern = r'attrs\s*=\s*["\']'
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            self.errors.append(ViewLintError(
                file_path, line_num, match.start(), "ODO18-002",
                'Deprecated attrs attribute found. Use direct attributes '
                '(invisible="expression", readonly="expression") instead',
                severity="ERROR"
            ))
    
    def _check_column_invisible_expressions(self, file_path: Path, content: str):
        """ODO18-003: Check for column_invisible with Python expressions"""
        # Match: column_invisible="something != 'value'" or similar
        # but NOT: column_invisible="1" or column_invisible="0" or column_invisible="field_name"
        pattern = r'column_invisible\s*=\s*["\']([^"\']+)["\']'
        
        for match in re.finditer(pattern, content):
            expression = match.group(1).strip()
            line_num = content[:match.start()].count('\n') + 1
            
            # Allow: "1", "0", single field names (no operators)
            if expression in ('0', '1', 'True', 'False'):
                continue
            
            # Check if it's a simple field name (alphanumeric + underscore only)
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', expression):
                continue
            
            # If it contains operators or complex expressions, it's an error
            if any(op in expression for op in ['!=', '==', '>', '<', '>=', '<=', 'and', 'or', 'not', '(']):
                self.errors.append(ViewLintError(
                    file_path, line_num, match.start(), "ODO18-003",
                    f'column_invisible with Python expression: "{expression}"\n'
                    f'  Python expressions are NOT evaluated in frontend, causing errors.\n'
                    f'  Solution: Use optional="show" or optional="hide" instead.\n'
                    f'  See: knowledge_base/10-frontend-views-odoo18.md',
                    severity="ERROR"
                ))
    
    def _check_ref_in_context(self, file_path: Path, content: str):
        """ODO18-004: Check for ref() in action context"""
        pattern = r'<field[^>]*name=["\']context["\'][^>]*>.*?ref\s*\([^)]+\).*?</field>'
        for match in re.finditer(pattern, content, re.DOTALL):
            line_num = content[:match.start()].count('\n') + 1
            self.errors.append(ViewLintError(
                file_path, line_num, match.start(), "ODO18-004",
                'ref() function in context not supported in Odoo 18.0+. '
                'Use XML ID directly or avoid ref() in context.',
                severity="ERROR"
            ))
    
    def _check_view_architecture(self, file_path: Path, tree: etree.Element):
        """Check view architecture for best practices"""
        # Check for views with <record model="ir.ui.view">
        for record in tree.xpath('//record[@model="ir.ui.view"]'):
            # Check if view has proper name
            name_field = record.find('field[@name="name"]')
            if name_field is None:
                self.errors.append(ViewLintError(
                    file_path, record.sourceline, 0, "VIEW001",
                    "View record missing 'name' field",
                    severity="WARNING"
                ))
            
            # Check if view has proper model
            model_field = record.find('field[@name="model"]')
            if model_field is None:
                self.errors.append(ViewLintError(
                    file_path, record.sourceline, 0, "VIEW002",
                    "View record missing 'model' field",
                    severity="WARNING"
                ))
    
    def check_directory(self, directory: Path, pattern: str = "*.xml"):
        """Recursively check all XML files in directory"""
        xml_files = list(directory.rglob(pattern))
        
        if not xml_files:
            print(f"{Colors.YELLOW}No XML files found in {directory}{Colors.NC}")
            return
        
        print(f"{Colors.BLUE}Found {len(xml_files)} XML files{Colors.NC}\n")
        
        for xml_file in xml_files:
            # Skip migration files and __pycache__
            if 'migration' in str(xml_file) or '__pycache__' in str(xml_file):
                continue
            
            self.check_file(xml_file)
    
    def print_report(self):
        """Print linting report"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"{Colors.BLUE}XML Linting Report{Colors.NC}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")
        
        if not self.errors:
            print(f"{Colors.GREEN}✓ No issues found!{Colors.NC}")
            print(f"Checked {self.checked_files} files.")
            return 0
        
        # Group errors by severity
        errors = [e for e in self.errors if e.severity == "ERROR"]
        warnings = [e for e in self.errors if e.severity == "WARNING"]
        
        # Print errors
        if errors:
            print(f"{Colors.RED}Errors: {len(errors)}{Colors.NC}\n")
            for error in errors:
                print(error)
                print()
        
        # Print warnings
        if warnings:
            print(f"{Colors.YELLOW}Warnings: {len(warnings)}{Colors.NC}\n")
            for warning in warnings:
                print(warning)
                print()
        
        # Summary
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}")
        print(f"Total issues: {len(self.errors)} "
              f"({len(errors)} errors, {len(warnings)} warnings)")
        print(f"Files checked: {self.checked_files}")
        print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")
        
        if errors:
            print(f"{Colors.RED}✗ Linting failed. Please fix errors before committing.{Colors.NC}")
            return 1
        elif warnings:
            print(f"{Colors.YELLOW}⚠ Linting passed with warnings.{Colors.NC}")
            return 0
        
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='XML Linter for Odoo Views - Detects Odoo 18.0 breaking changes'
    )
    parser.add_argument(
        'path',
        type=Path,
        help='File or directory to check'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--pattern',
        default='*.xml',
        help='File pattern to match (default: *.xml)'
    )
    
    args = parser.parse_args()
    
    # Banner
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}Odoo XML View Linter - Odoo 18.0{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")
    
    linter = OdooViewLinter(verbose=args.verbose)
    
    if args.path.is_file():
        linter.check_file(args.path)
    elif args.path.is_dir():
        linter.check_directory(args.path, args.pattern)
    else:
        print(f"{Colors.RED}Error: Path not found: {args.path}{Colors.NC}")
        return 1
    
    return linter.print_report()


if __name__ == '__main__':
    sys.exit(main())
