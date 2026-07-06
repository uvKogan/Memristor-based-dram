---
argument-hint: [skill_name] [desired_behavior]
description: Meta-command to generate a new MBMM custom slash command.
---
Based on the user's request: $ARGUMENTS
Create a new file named `.claude/commands/mbmm_<skill_name>.md`. 
Automatically write the YAML frontmatter (including `description` and `argument-hint` if applicable) and translate the desired behavior into a robust prompt instruction. Save the file and confirm the new command is ready to use.
