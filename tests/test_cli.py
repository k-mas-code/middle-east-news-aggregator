"""
Tests for CLI interface.

Validates: Requirements 1.2, 1.6, 7.3, 7.4
"""

import pytest
from unittest.mock import patch, Mock
import sys


class TestCLI:
    """Tests for command-line interface."""

    @pytest.mark.unit
    def test_cli_collect_success(self, mock_firestore_client, capsys):
        """
        Test CLI collect command with successful execution.

        Validates: Requirements 1.2, 1.6
        """
        from middle_east_aggregator import cli

        # Mock the pipeline to return success
        mock_pipeline = Mock()
        mock_pipeline.run.return_value = {
            'status': 'success',
            'articles_collected': 50,
            'articles_filtered': 15,
            'clusters_created': 5,
            'reports_generated': 5,
            'duration_seconds': 45.2
        }

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            with patch('middle_east_aggregator.cli.NewsPipeline', return_value=mock_pipeline):
                # When: We run the collect command
                sys.argv = ['cli.py', 'collect']
                exit_code = cli.main()

                # Then: Should succeed
                assert exit_code == 0

                # And: Should print summary
                captured = capsys.readouterr()
                assert 'COLLECTION SUMMARY' in captured.out
                assert 'Status: SUCCESS' in captured.out
                assert 'Articles collected: 50' in captured.out
                assert 'Articles filtered: 15' in captured.out
                assert 'Clusters created: 5' in captured.out
                assert 'Reports generated: 5' in captured.out

    @pytest.mark.unit
    def test_cli_collect_error(self, mock_firestore_client, capsys):
        """
        Test CLI collect command with error.

        Validates: Requirements 7.3, 7.4
        """
        from middle_east_aggregator import cli

        # Mock the pipeline to return error
        mock_pipeline = Mock()
        mock_pipeline.run.return_value = {
            'status': 'error',
            'error': 'Network timeout',
            'articles_collected': 10,
            'articles_filtered': 3
        }

        with patch('middle_east_aggregator.database.firestore.Client', return_value=mock_firestore_client):
            with patch('middle_east_aggregator.cli.NewsPipeline', return_value=mock_pipeline):
                # When: We run the collect command
                sys.argv = ['cli.py', 'collect']
                exit_code = cli.main()

                # Then: Should fail
                assert exit_code == 1

                # And: Should print error
                captured = capsys.readouterr()
                assert 'COLLECTION SUMMARY' in captured.out
                assert 'Error: Network timeout' in captured.out

    @pytest.mark.unit
    def test_cli_unknown_command(self, capsys):
        """
        Test CLI with unknown command.
        """
        from middle_east_aggregator import cli

        # When: We run with unknown command
        sys.argv = ['cli.py', 'unknown']
        exit_code = cli.main()

        # Then: Should fail
        assert exit_code == 1

        # And: Should print error
        captured = capsys.readouterr()
        assert 'Unknown command: unknown' in captured.out

    @pytest.mark.unit
    def test_cli_no_command(self, capsys):
        """
        Test CLI without command.
        """
        from middle_east_aggregator import cli

        # When: We run without command
        sys.argv = ['cli.py']
        exit_code = cli.main()

        # Then: Should fail
        assert exit_code == 1

        # And: Should print usage
        captured = capsys.readouterr()
        assert 'Usage:' in captured.out

    @pytest.mark.unit
    def test_format_duration(self):
        """
        Test duration formatting.
        """
        from middle_east_aggregator.cli import format_duration

        # Test seconds
        assert format_duration(45.2) == "45.2s"

        # Test minutes
        assert format_duration(120) == "2.0m"

        # Test hours
        assert format_duration(3661) == "1.0h"

    @pytest.mark.unit
    def test_print_summary_success(self, capsys):
        """
        Test summary printing for successful collection.
        """
        from middle_east_aggregator.cli import print_summary

        result = {
            'status': 'success',
            'articles_collected': 50,
            'articles_filtered': 15,
            'clusters_created': 5,
            'reports_generated': 5,
            'duration_seconds': 45.2
        }

        # When: We print summary
        print_summary(result)

        # Then: Should print all statistics
        captured = capsys.readouterr()
        assert 'COLLECTION SUMMARY' in captured.out
        assert 'Status: SUCCESS' in captured.out
        assert 'Articles collected: 50' in captured.out
        assert 'Filter rate: 30.0%' in captured.out

    @pytest.mark.unit
    def test_print_summary_error(self, capsys):
        """
        Test summary printing for failed collection.
        """
        from middle_east_aggregator.cli import print_summary

        result = {
            'status': 'error',
            'error': 'Database connection failed',
            'articles_collected': 10,
            'articles_filtered': 3
        }

        # When: We print summary
        print_summary(result)

        # Then: Should print error and partial results
        captured = capsys.readouterr()
        assert 'COLLECTION SUMMARY' in captured.out
        assert 'Error: Database connection failed' in captured.out
        assert 'Partial - Articles collected: 10' in captured.out
