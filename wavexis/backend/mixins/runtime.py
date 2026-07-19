"""Runtime mixin — JavaScript evaluation, script compilation, and object management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RuntimeBackend(ABC):
    """Runtime evaluation, script compilation, and remote object management."""

    @abstractmethod
    async def runtime_evaluate(
        self,
        expression: str,
        await_promise: bool = False,
        return_by_value: bool = False,
    ) -> dict[str, Any]:
        """Evaluate a JavaScript expression.

        Args:
            expression: JavaScript expression to evaluate.
            await_promise: Whether to await the resulting promise.
            return_by_value: Whether to return the result by value.

        Returns:
            The evaluation result as a dict.
        """

    @abstractmethod
    async def runtime_compile_script(
        self,
        expression: str,
        source_url: str = "",
        persist_script: bool = False,
    ) -> dict[str, Any]:
        """Compile a JavaScript expression without running it.

        Args:
            expression: JavaScript expression to compile.
            source_url: Source URL for the script.
            persist_script: Whether the script should persist.

        Returns:
            The compilation result with scriptId.
        """

    @abstractmethod
    async def runtime_run_script(
        self, script_id: str, await_promise: bool = False
    ) -> dict[str, Any]:
        """Run a previously compiled script by ID.

        Args:
            script_id: ID of the compiled script.
            await_promise: Whether to await the resulting promise.

        Returns:
            The evaluation result as a dict.
        """

    @abstractmethod
    async def runtime_call_function_on(
        self,
        function_declaration: str,
        object_id: str = "",
        arguments: list[dict[str, Any]] | None = None,
        await_promise: bool = False,
        return_by_value: bool = False,
    ) -> dict[str, Any]:
        """Call a function on a remote object.

        Args:
            function_declaration: JavaScript function declaration.
            object_id: Remote object ID to call on.
            arguments: List of argument dicts.
            await_promise: Whether to await the resulting promise.
            return_by_value: Whether to return the result by value.

        Returns:
            The call result as a dict.
        """

    @abstractmethod
    async def runtime_get_properties(
        self, object_id: str, own_properties: bool = True
    ) -> dict[str, Any]:
        """Get properties of a remote object.

        Args:
            object_id: Remote object ID.
            own_properties: Whether to get own properties only.

        Returns:
            The properties result as a dict.
        """

    @abstractmethod
    async def runtime_release_object(self, object_id: str) -> None:
        """Release a remote object.

        Args:
            object_id: Remote object ID to release.
        """

    @abstractmethod
    async def runtime_release_object_group(self, object_group: str) -> None:
        """Release all objects in a group.

        Args:
            object_group: Object group name to release.
        """

    @abstractmethod
    async def runtime_discard_console_entries(self) -> None:
        """Discard collected console entries."""

    @abstractmethod
    async def runtime_get_heap_usage(self) -> dict[str, Any]:
        """Get the current heap usage.

        Returns:
            A dict with usedSize and totalSize.
        """

    @abstractmethod
    async def runtime_global_lexical_scope_names(
        self, execution_context_id: int | None = None
    ) -> dict[str, Any]:
        """Get global lexical scope names.

        Args:
            execution_context_id: Execution context ID.

        Returns:
            A dict with names list.
        """

    @abstractmethod
    async def runtime_add_binding(
        self, name: str, execution_context_name: str | None = None
    ) -> None:
        """Add a binding with the given name on the global objects of all execution contexts.

        Args:
            name: Binding name.
            execution_context_name: Optional execution context name filter.
        """

    @abstractmethod
    async def runtime_await_promise(
        self, promise_object_id: str, return_by_value: bool = False
    ) -> dict[str, Any]:
        """Await a promise by its remote object ID.

        Args:
            promise_object_id: Remote object ID of the promise.
            return_by_value: Whether to return the result by value.

        Returns:
            The await result as a dict.
        """

    @abstractmethod
    async def runtime_collect_garbage(self) -> None:
        """Collect garbage."""

    @abstractmethod
    async def runtime_disable(self) -> None:
        """Disable the Runtime domain."""

    @abstractmethod
    async def runtime_enable(self) -> None:
        """Enable the Runtime domain."""

    @abstractmethod
    async def runtime_get_exception_details(self, error_object_id: str) -> dict[str, Any]:
        """Get exception details for an error object.

        Args:
            error_object_id: Remote object ID of the error.

        Returns:
            Dict with exception details.
        """

    @abstractmethod
    async def runtime_get_isolate_id(self) -> dict[str, Any]:
        """Get the isolate ID.

        Returns:
            Dict containing the isolate ID.
        """

    @abstractmethod
    async def runtime_query_objects(self, prototype_object_id: str) -> dict[str, Any]:
        """Query objects by prototype.

        Args:
            prototype_object_id: Remote object ID of the prototype.

        Returns:
            Dict with objects result.
        """

    @abstractmethod
    async def runtime_remove_binding(self, name: str) -> None:
        """Remove a previously added binding.

        Args:
            name: Binding name to remove.
        """

    @abstractmethod
    async def runtime_run_if_waiting_for_debugger(self) -> None:
        """Run if waiting for debugger to pause."""

    @abstractmethod
    async def runtime_set_async_call_stack_depth(self, max_depth: int) -> None:
        """Set the async call stack depth.

        Args:
            max_depth: Maximum depth of async call stacks.
        """

    @abstractmethod
    async def runtime_set_custom_object_formatter_enabled(self, enabled: bool) -> None:
        """Enable or disable the custom object formatter.

        Args:
            enabled: Whether to enable the custom formatter.
        """

    @abstractmethod
    async def runtime_set_max_call_stack_size_to_capture(self, size: int) -> None:
        """Set the max call stack size to capture.

        Args:
            size: Maximum call stack size.
        """

    @abstractmethod
    async def runtime_terminate_execution(self) -> None:
        """Terminate the current execution."""
