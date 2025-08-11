def get_functions():
    return [
            {
                "name": "access_to_redmine",
                "description": "Check access to Redmine",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "API key for Redmine access"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "get_issue_by_date",
                "description": "Get issue details by date",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date of the issue"}
                    },
                    "required": ["date"]
                }
            },
            {
                "name": "get_issue_by_id",
                "description": "Get issue #453799 details by ID",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "id": {"type": "string", "description": "ID of the issue"}
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "get_issue_by_name",
                "description": "Get issue #453799 details by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the issue"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_issue_status",
                "description": "Get issue #453799 status by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the issue #453799"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_my_issues",
                "description": "Get my issues",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the issue"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_issue_hours",
                "description": "Get issue #453799 hours by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the issue #453799"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_user_status",
                "description": "Get user status by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the user"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "fill_issue_hours",
                "description": "Fill issue #453799 5 hours I did some hotfix issue by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Short description of fixing the issue"},
                        "hours": {"type": "number", "description": "Number of hours spent on the issue"},
                        "description": {"type": "string", "description": "Description of the work done"}
                    },
                    "required": ["name", "hours", "description"]
                }
            },
            {
                "name": "get_wiki_info",
                "description": "Get wiki information by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the wiki"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "set_user_status",
                "description": "Set user status by name",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the user"},
                        "status": {"type": "string", "description": "New status of the user"}
                    },
                    "required": ["name", "status"]
                }
            },
            {
                "name": "create_issue",
                "description": "Create a new issue",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "name": {"type": "string", "description": "Name of the issue"},
                        "description": {"type": "string", "description": "Description of the issue"}
                    },
                    "required": ["name", "description"]
                }
            },
            {
                "name": "assign_issue",
                "description": "Assign an issue to a user",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "issue_name": {"type": "string", "description": "Name of the issue"},
                        "user_name": {"type": "string", "description": "Name of the user"}
                    },
                    "required": ["issue_name", "user_name"]
                }
            },
        ]