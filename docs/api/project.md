# Project Management API

The public interface used to create and manage a MicroGridsPy project. A project is a
folder containing a `formulation.json` plus CSV/YAML input templates; these functions
create, validate, and manipulate that folder.

The workflow distinguishes clearly between **creating** a project, **validating** its
inputs, and **running** the optimization (documented under [Optimization](optimization.md)).

## `create_project`

::: microgridspy.create_project

## `validate_project`

::: microgridspy.validate_project

## `copy_project`

::: microgridspy.copy_project

## `rename_project`

::: microgridspy.rename_project

## `delete_project`

::: microgridspy.delete_project

## `TemplateSettings`

For full control over the generated input templates, build a `TemplateSettings` object and
pass it to `create_project(..., settings=...)`.

::: microgridspy.TemplateSettings
