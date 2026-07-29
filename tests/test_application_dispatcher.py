"""Tests for the application command dispatcher spike."""

from __future__ import annotations

import unittest
from dataclasses import dataclass

from src.application.dispatcher import (
    ApplicationCommandDispatcher,
    ErrorResult,
    SuccessResult,
)


@dataclass(frozen=True)
class ExampleCommand:
    value: str
    command_name: str = "example.run"



class ApplicationCommandDispatcherTest(unittest.TestCase):
    def test_dispatches_registered_command(self) -> None:
        dispatcher = ApplicationCommandDispatcher()
        dispatcher.register("example.run", lambda command: command.value.upper())

        result = dispatcher.dispatch(ExampleCommand("wert"))

        self.assertIsInstance(result, SuccessResult)
        self.assertEqual(result.value, "WERT")
        self.assertEqual(dispatcher.registered_commands(), ("example.run",))

    def test_rejects_unknown_command(self) -> None:
        dispatcher = ApplicationCommandDispatcher()

        result = dispatcher.dispatch(ExampleCommand("wert"))

        self.assertIsInstance(result, ErrorResult)
        self.assertFalse(result.success)
        self.assertEqual(result.command_name, "example.run")


if __name__ == "__main__":
    unittest.main()
