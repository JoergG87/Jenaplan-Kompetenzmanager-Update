"""Old mutation authority stays unreachable even if callers retain old objects."""
import ast
import importlib
from pathlib import Path

import pytest

from src.core.schema_upgrade import UpgradeError
from src.security.infrastructure.upgrade_journal_repository import UpgradeJournalCodec
from src.security.infrastructure.upgrade_replay_anchor import UpgradeReplayCodec


OLD_APIS = (
    ('src.security.infrastructure.upgrade_process_lease', 'UpgradeProcessLease'),
    ('src.security.infrastructure.upgrade_atomic_activation', 'SyntheticUpgradeActivation'),
    ('src.security.infrastructure.upgrade_atomic_activation', 'PinnedUpgradeFiles'),
    ('src.security.infrastructure.upgrade_journal_repository', 'AuthenticatedUpgradeJournalRepository'),
    ('src.security.infrastructure.upgrade_replay_anchor', 'UpgradeReplayAnchorRepository'),
    ('src.security.infrastructure.upgrade_rollback_source', 'DurableUpgradeRollbackSource'),
    ('src.security.infrastructure.encrypted_upgrade_source', 'EncryptedUpgradeSourceAdapter'),
    ('src.application.commands.schema_upgrade', 'UpgradeMaintenance'),
    ('src.application.commands.prepare_upgrade_source', 'PrepareEncryptedUpgradeSource'),
)


@pytest.mark.parametrize('module,name', OLD_APIS)
def test_old_api_has_no_mutation_or_authority_even_with_legacy_object(module, name):
    api = getattr(importlib.import_module(module), name)
    with pytest.raises(UpgradeError, match='upgrade_file_exchange_retired'): api()
    for entry in ('__enter__', 'require_owner', 'execute', 'create', 'save', 'create_backup', 'create_staging', 'verify'):
        with pytest.raises(UpgradeError, match='upgrade_file_exchange_retired'):
            getattr(api, entry)(object(), object(), arbitrary='old deserialized context')


@pytest.mark.parametrize('codec', [UpgradeJournalCodec, UpgradeReplayCodec])
def test_product_historical_codecs_have_no_filesystem_methods(codec):
    assert not any(hasattr(codec, name) for name in (
        'create','save','load','load_with_digest','_read_regular_bytes','_write_atomic','delete_completed'))


def test_product_modules_cannot_import_historical_execution_or_test_commit_vfs():
    root = Path(__file__).resolve().parents[1]
    for path in (root/'src').rglob('*.py'):
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith(('tests.historical_upgrade', 'tests.helpers.sqlcipher_commit_probe')) for alias in node.names), path
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith(('tests.historical_upgrade', 'tests.helpers.sqlcipher_commit_probe')), path
        assert 'historical_upgrade' not in source, path
        assert 'SQLCipherCommitProbe' not in source, path
    # Retain the exact original nine failing assertions as historical evidence,
    # not collected or silently converted into an acceptance of unsafe behavior.
    baseline = root/'tests/historical_upgrade/ownership_counterexamples.py'
    assert 'Journal advanced after kernel lock loss' in baseline.read_text()
    assert baseline.read_text().count('lease.require_owner(ctx)') >= 4
    spec = ast.parse((root/'packaging/macos_pilot.spec').read_text())
    analysis = next(node for node in ast.walk(spec) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == 'Analysis')
    excludes = next(kw.value for kw in analysis.keywords if kw.arg == 'excludes')
    names = {node.value for node in ast.walk(excludes) if isinstance(node, ast.Constant)}
    assert {'tests.historical_upgrade', 'tests.helpers.sqlcipher_commit_probe'} <= names
