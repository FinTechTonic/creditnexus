"""
Unit tests for document extraction chains.

Tests simple extraction, map-reduce extraction, error handling, and retry logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from decimal import Decimal
from pydantic import ValidationError

from app.chains.extraction_chain import (
    create_extraction_chain,
    create_extraction_prompt,
    extract_data,
    extract_data_smart,
    MAP_REDUCE_THRESHOLD,
    AGENTIC_PIPELINE_THRESHOLD
)
from app.chains.map_reduce_chain import (
    create_partial_extraction_chain,
    create_partial_extraction_prompt,
    extract_data_map_reduce
)
from app.models.cdm import (
    CreditAgreement,
    ExtractionResult,
    ExtractionStatus,
    Party,
    LoanFacility,
    Money,
    Currency,
    GoverningLaw,
    Frequency,
    PeriodEnum,
    InterestRatePayout,
    FloatingRateOption
)


@pytest.fixture
def sample_credit_agreement_text():
    """Sample credit agreement text for testing."""
    return """
    CREDIT AGREEMENT
    
    This Credit Agreement is entered into on January 15, 2024, between:
    
    BORROWER: Acme Corporation, a Delaware corporation
    
    LENDER: First National Bank, a New York banking corporation
    
    FACILITY: Revolving Credit Facility
    Amount: $10,000,000.00 USD
    Maturity Date: January 15, 2029
    Interest Rate: SOFR + 2.50% (250 basis points)
    Payment Frequency: Quarterly
    
    GOVERNING LAW: New York
    """


@pytest.fixture
def sample_long_credit_agreement_text():
    """Sample long credit agreement text (>50k chars) for map-reduce testing."""
    base_text = """
    CREDIT AGREEMENT
    
    This Credit Agreement is entered into on January 15, 2024.
    
    ARTICLE I - DEFINITIONS
    
    Section 1.01. Definitions. As used in this Agreement, the following terms shall have the meanings set forth below:
    """
    # Create a long document by repeating sections
    long_text = base_text * 2000  # Should exceed 50k chars
    return long_text


@pytest.fixture
def mock_extraction_result():
    """Mock ExtractionResult for testing."""
    from app.models.cdm import InterestRatePayout, FloatingRateOption
    
    return ExtractionResult(
        agreement=CreditAgreement(
            deal_id="DEAL_2024_001",
            agreement_date=date(2024, 1, 15),
            governing_law=GoverningLaw.NY,
            parties=[
                Party(
                    id="party_1",
                    name="Acme Corporation",
                    role="Borrower"
                ),
                Party(
                    id="party_2",
                    name="First National Bank",
                    role="Lender"
                )
            ],
            facilities=[
                LoanFacility(
                    facility_name="Revolving Credit Facility",
                    commitment_amount=Money(
                        amount=Decimal("10000000.00"),
                        currency=Currency.USD
                    ),
                    maturity_date=date(2029, 1, 15),
                    interest_terms=InterestRatePayout(
                        rate_option=FloatingRateOption(
                            benchmark="SOFR",
                            spread_bps=250.0
                        ),
                        payment_frequency=Frequency(
                            period=PeriodEnum.Month,
                            period_multiplier=3
                        )
                    )
                )
            ]
        ),
        status=ExtractionStatus.SUCCESS,
        message="Extraction completed successfully"
    )


class TestExtractionChainCreation:
    """Tests for extraction chain creation functions."""
    
    @patch('app.chains.extraction_chain.get_chat_model')
    def test_create_extraction_chain(self, mock_get_chat_model):
        """Test extraction chain creation."""
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_llm.with_structured_output.return_value = mock_structured_llm
        mock_get_chat_model.return_value = mock_llm
        
        chain = create_extraction_chain()
        
        assert chain is not None
        mock_get_chat_model.assert_called_once_with(temperature=0)
        mock_llm.with_structured_output.assert_called_once_with(ExtractionResult)
    
    def test_create_extraction_prompt(self):
        """Test extraction prompt creation."""
        prompt = create_extraction_prompt()
        
        assert prompt is not None
        # Check that prompt has system and user messages
        messages = prompt.messages
        assert len(messages) == 2
        assert messages[0].prompt.template  # System message
        assert messages[1].prompt.template  # User message


class TestSimpleExtraction:
    """Tests for simple extraction (<50k chars)."""
    
    @patch('app.chains.extraction_chain.create_extraction_chain')
    @patch('app.chains.extraction_chain.create_extraction_prompt')
    def test_extract_data_success(self, mock_prompt, mock_chain, sample_credit_agreement_text, mock_extraction_result):
        """Test successful simple extraction."""
        # Setup mocks
        mock_prompt_instance = Mock()
        mock_prompt.return_value = mock_prompt_instance
        
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance
        
        mock_extraction_chain = Mock()
        mock_extraction_chain.invoke.return_value = mock_extraction_result
        mock_prompt_instance.__or__ = Mock(return_value=mock_extraction_chain)
        
        # Execute
        result = extract_data(sample_credit_agreement_text, max_retries=3)
        
        # Verify
        assert result is not None
        assert result.status == ExtractionStatus.SUCCESS
        assert result.agreement is not None
        mock_extraction_chain.invoke.assert_called_once()
    
    @patch('app.chains.extraction_chain.create_extraction_chain')
    @patch('app.chains.extraction_chain.create_extraction_prompt')
    def test_extract_data_retry_on_validation_error(self, mock_prompt, mock_chain, sample_credit_agreement_text, mock_extraction_result):
        """Test retry logic on validation error."""
        # Setup mocks
        mock_prompt_instance = Mock()
        mock_prompt.return_value = mock_prompt_instance
        
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance
        
        mock_extraction_chain = Mock()
        # First call fails with ValidationError, second succeeds
        # Create a real ValidationError by trying to validate invalid data
        try:
            CreditAgreement(agreement_date=None, parties=None, facilities=None, governing_law=None)
            validation_error = ValidationError.from_exception_data(
                "CreditAgreement",
                [{"type": "missing", "loc": ("agreement_date",), "msg": "Field required", "input": None}]
            )
        except ValidationError as ve:
            validation_error = ve
        
        mock_extraction_chain.invoke.side_effect = [
            validation_error,
            mock_extraction_result
        ]
        mock_prompt_instance.__or__ = Mock(return_value=mock_extraction_chain)
        
        # Execute
        result = extract_data(sample_credit_agreement_text, max_retries=3)
        
        # Verify
        assert result is not None
        assert result.status == ExtractionStatus.SUCCESS
        # Should have been called twice (initial + retry)
        assert mock_extraction_chain.invoke.call_count == 2
    
    @patch('app.chains.extraction_chain.create_extraction_chain')
    @patch('app.chains.extraction_chain.create_extraction_prompt')
    def test_extract_data_max_retries_exceeded(self, mock_prompt, mock_chain, sample_credit_agreement_text):
        """Test that ValueError is raised when max retries exceeded."""
        # Setup mocks
        mock_prompt_instance = Mock()
        mock_prompt.return_value = mock_prompt_instance
        
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance
        
        mock_extraction_chain = Mock()
        # Always fail with ValidationError - create a real one
        try:
            CreditAgreement(agreement_date=None, parties=None, facilities=None, governing_law=None)
            validation_error = None
        except ValidationError as ve:
            validation_error = ve
        
        if validation_error is None:
            # Fallback: create a simple ValidationError
            validation_error = ValidationError.from_exception_data(
                "CreditAgreement",
                [{"type": "missing", "loc": ("agreement_date",), "msg": "Field required", "input": None}]
            )
        
        mock_extraction_chain.invoke.side_effect = validation_error
        mock_prompt_instance.__or__ = Mock(return_value=mock_extraction_chain)
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Extracted data failed validation"):
            extract_data(sample_credit_agreement_text, max_retries=2)
        
        # Should have been called max_retries times
        assert mock_extraction_chain.invoke.call_count == 2


class TestSmartExtraction:
    """Tests for smart extraction with automatic strategy selection."""
    
    def test_extract_data_smart_small_document(self, sample_credit_agreement_text):
        """Test smart extraction selects simple extraction for small documents."""
        with patch('app.chains.extraction_chain.extract_data') as mock_extract:
            mock_extract.return_value = Mock(spec=ExtractionResult)
            
            result = extract_data_smart(sample_credit_agreement_text, max_retries=3)
            
            assert result is not None
            mock_extract.assert_called_once_with(sample_credit_agreement_text, max_retries=3)
    
    def test_extract_data_smart_large_document(self, sample_long_credit_agreement_text):
        """Test smart extraction selects map-reduce for large documents."""
        with patch('app.chains.extraction_chain.extract_data_map_reduce') as mock_map_reduce:
            mock_map_reduce.return_value = Mock(spec=ExtractionResult)
            
            result = extract_data_smart(sample_long_credit_agreement_text, max_retries=3)
            
            assert result is not None
            mock_map_reduce.assert_called_once_with(sample_long_credit_agreement_text)
    
    def test_extract_data_smart_force_map_reduce(self, sample_credit_agreement_text):
        """Test force_map_reduce parameter."""
        with patch('app.chains.extraction_chain.extract_data_map_reduce') as mock_map_reduce:
            mock_map_reduce.return_value = Mock(spec=ExtractionResult)
            
            result = extract_data_smart(sample_credit_agreement_text, force_map_reduce=True, max_retries=3)
            
            assert result is not None
            mock_map_reduce.assert_called_once_with(sample_credit_agreement_text)
    
    def test_extract_data_smart_threshold_boundary(self):
        """Test threshold boundary behavior."""
        # Test exactly at threshold
        text_at_threshold = "x" * MAP_REDUCE_THRESHOLD
        
        with patch('app.chains.extraction_chain.extract_data') as mock_extract:
            mock_extract.return_value = Mock(spec=ExtractionResult)
            
            result = extract_data_smart(text_at_threshold, max_retries=3)
            
            # Should use simple extraction (threshold is exclusive)
            mock_extract.assert_called_once()
        
        # Test just over threshold
        text_over_threshold = "x" * (MAP_REDUCE_THRESHOLD + 1)
        
        with patch('app.chains.extraction_chain.extract_data_map_reduce') as mock_map_reduce:
            mock_map_reduce.return_value = Mock(spec=ExtractionResult)
            
            result = extract_data_smart(text_over_threshold, max_retries=3)
            
            # Should use map-reduce
            mock_map_reduce.assert_called_once()


class TestMapReduceExtraction:
    """Tests for map-reduce extraction chain."""
    
    @patch('app.chains.map_reduce_chain.CreditAgreementSplitter')
    @patch('app.chains.map_reduce_chain.create_partial_extraction_prompt')
    @patch('app.chains.map_reduce_chain.create_partial_extraction_chain')
    @patch('app.chains.map_reduce_chain.create_reducer_prompt')
    @patch('app.chains.map_reduce_chain.create_reducer_chain')
    def test_extract_data_map_reduce_success(
        self,
        mock_reducer_chain,
        mock_reducer_prompt,
        mock_partial_chain,
        mock_partial_prompt,
        mock_splitter,
        sample_long_credit_agreement_text,
        mock_extraction_result
    ):
        """Test successful map-reduce extraction."""
        # Setup splitter
        mock_splitter_instance = Mock()
        mock_chunk = Mock()
        mock_chunk.text = "Article I text"
        mock_chunk.article_title = "Article I"
        mock_chunk.article_number = 1
        mock_chunk.chunk_index = 0
        mock_splitter_instance.split_by_articles.return_value = [mock_chunk]
        mock_splitter.return_value = mock_splitter_instance
        
        # Setup partial extraction chain
        mock_partial_prompt_instance = Mock()
        mock_partial_prompt.return_value = mock_partial_prompt_instance
        mock_partial_chain_instance = Mock()
        mock_partial_chain.return_value = mock_partial_chain_instance
        mock_partial_extraction_chain = Mock()
        mock_partial_extraction_chain.invoke.return_value = Mock()  # PartialCreditAgreement
        mock_partial_prompt_instance.__or__ = Mock(return_value=mock_partial_extraction_chain)
        
        # Setup reducer chain
        mock_reducer_prompt_instance = Mock()
        mock_reducer_prompt.return_value = mock_reducer_prompt_instance
        mock_reducer_chain_instance = Mock()
        mock_reducer_chain.return_value = mock_reducer_chain_instance
        mock_reducer_extraction_chain = Mock()
        mock_reducer_extraction_chain.invoke.return_value = mock_extraction_result
        mock_reducer_prompt_instance.__or__ = Mock(return_value=mock_reducer_extraction_chain)
        
        # Execute
        result = extract_data_map_reduce(sample_long_credit_agreement_text)
        
        # Verify
        assert result is not None
        assert result.status == ExtractionStatus.SUCCESS
        mock_splitter_instance.split_by_articles.assert_called_once()
        mock_partial_extraction_chain.invoke.assert_called()
        mock_reducer_extraction_chain.invoke.assert_called_once()
    
    @patch('app.chains.map_reduce_chain.CreditAgreementSplitter')
    @patch('app.chains.map_reduce_chain.create_partial_extraction_prompt')
    @patch('app.chains.map_reduce_chain.create_partial_extraction_chain')
    @patch('app.core.llm_client.get_chat_model')
    def test_extract_data_map_reduce_no_chunks(
        self,
        mock_get_chat_model,
        mock_partial_chain,
        mock_partial_prompt,
        mock_splitter,
        sample_long_credit_agreement_text
    ):
        """Test map-reduce extraction with no chunks."""
        # Setup splitter to return empty list
        mock_splitter_instance = Mock()
        mock_splitter_instance.split_by_articles.return_value = []
        mock_splitter.return_value = mock_splitter_instance
        
        # Mock LLM to avoid initialization error
        mock_llm = Mock()
        mock_get_chat_model.return_value = mock_llm
        
        # Mock chain components
        mock_partial_prompt_instance = Mock()
        mock_partial_prompt.return_value = mock_partial_prompt_instance
        mock_partial_chain_instance = Mock()
        mock_partial_chain.return_value = mock_partial_chain_instance
        mock_partial_extraction_chain = Mock()
        mock_partial_prompt_instance.__or__ = Mock(return_value=mock_partial_extraction_chain)
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="No partial extractions were successful"):
            extract_data_map_reduce(sample_long_credit_agreement_text)


class TestCDMValidation:
    """Tests for CDM model validation."""
    
    def test_extraction_result_validation(self):
        """Test ExtractionResult model validation."""
        # Valid ExtractionResult
        result = ExtractionResult(
            agreement=CreditAgreement(
                deal_id="DEAL_001",
                agreement_date=date(2024, 1, 15),
                governing_law=GoverningLaw.NY,
                parties=[
                    Party(id="p1", name="Borrower", role="Borrower")
                ],
                facilities=[
                    LoanFacility(
                        facility_name="Facility 1",
                        commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
                        maturity_date=date(2029, 1, 15),
                        interest_terms=InterestRatePayout(
                            rate_option=FloatingRateOption(
                                benchmark="SOFR",
                                spread_bps=250.0
                            ),
                            payment_frequency=Frequency(
                                period=PeriodEnum.Month,
                                period_multiplier=3
                            )
                        )
                    )
                ]
            ),
            status=ExtractionStatus.SUCCESS
        )
        
        assert result.status == ExtractionStatus.SUCCESS
        assert result.agreement is not None
    
    def test_extraction_result_invalid_status(self):
        """Test that invalid status raises ValidationError."""
        with pytest.raises(ValidationError):
            ExtractionResult(
                agreement=CreditAgreement(
                    deal_id="DEAL_001",
                    agreement_date=date(2024, 1, 15),
                    governing_law=GoverningLaw.NY,
                    parties=[Party(id="p1", name="Borrower", role="Borrower")],
                    facilities=[]
                ),
                status="invalid_status"  # Invalid status
            )


class TestErrorHandling:
    """Tests for error handling in extraction chains."""
    
    @patch('app.chains.extraction_chain.create_extraction_chain')
    @patch('app.chains.extraction_chain.create_extraction_prompt')
    def test_extract_data_unexpected_error(self, mock_prompt, mock_chain, sample_credit_agreement_text):
        """Test handling of unexpected errors."""
        # Setup mocks
        mock_prompt_instance = Mock()
        mock_prompt.return_value = mock_prompt_instance
        
        mock_chain_instance = Mock()
        mock_chain.return_value = mock_chain_instance
        
        mock_extraction_chain = Mock()
        mock_extraction_chain.invoke.side_effect = Exception("Unexpected error")
        mock_prompt_instance.__or__ = Mock(return_value=mock_extraction_chain)
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Extraction failed"):
            extract_data(sample_credit_agreement_text, max_retries=3)


class TestIntegration:
    """Integration tests for extraction chains."""
    
    def test_extract_data_smart_integration_flow(self, sample_credit_agreement_text):
        """Test the complete integration flow of smart extraction."""
        # This is a smoke test - actual LLM calls would be mocked in real tests
        # For now, we test that the function doesn't crash with valid input
        with patch('app.chains.extraction_chain.extract_data') as mock_extract:
            mock_result = Mock(spec=ExtractionResult)
            mock_result.status = ExtractionStatus.SUCCESS
            mock_extract.return_value = mock_result
            
            result = extract_data_smart(sample_credit_agreement_text)
            
            assert result is not None
            mock_extract.assert_called_once()
