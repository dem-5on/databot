import pytest
from app.utils.phone_utils import (
    normalize_phone_number,
    validate_phone_number,
    detect_network,
    format_phone_for_display
)


class TestNormalizePhoneNumber:
    """Tests for normalize_phone_number function."""
    
    @pytest.mark.unit
    def test_local_format_with_leading_zero(self):
        """Test normalizing local format (0XXXXXXXXX)."""
        assert normalize_phone_number("0241234567") == "233241234567"
    
    @pytest.mark.unit
    def test_local_format_with_spaces(self):
        """Test normalizing with spaces."""
        assert normalize_phone_number("024 123 4567") == "233241234567"
    
    @pytest.mark.unit
    def test_local_format_with_dashes(self):
        """Test normalizing with dashes."""
        assert normalize_phone_number("024-123-4567") == "233241234567"
    
    @pytest.mark.unit
    def test_international_format_with_plus(self):
        """Test normalizing international format (+233XXXXXXXXX)."""
        assert normalize_phone_number("+233241234567") == "233241234567"
    
    @pytest.mark.unit
    def test_international_format_without_plus(self):
        """Test normalizing international format (233XXXXXXXXX)."""
        assert normalize_phone_number("233241234567") == "233241234567"
    
    @pytest.mark.unit
    def test_custom_country_code(self):
        """Test with custom country code."""
        assert normalize_phone_number("0241234567", "234") == "234241234567"
    
    @pytest.mark.unit
    def test_multiple_leading_zeros(self):
        """Test stripping multiple leading zeros."""
        assert normalize_phone_number("00241234567") == "233241234567"


class TestValidatePhoneNumber:
    """Tests for validate_phone_number function."""
    
    @pytest.mark.unit
    def test_valid_local_format(self):
        """Test valid local format (10 digits)."""
        is_valid, error = validate_phone_number("0241234567")
        assert is_valid is True
        assert error == ""
    
    @pytest.mark.unit
    def test_valid_international_format(self):
        """Test valid international format (12 digits)."""
        is_valid, error = validate_phone_number("233241234567")
        assert is_valid is True
        assert error == ""
    
    @pytest.mark.unit
    def test_valid_without_prefix(self):
        """Test valid 9-digit number without prefix."""
        is_valid, error = validate_phone_number("241234567")
        assert is_valid is True
        assert error == ""
    
    @pytest.mark.unit
    def test_invalid_non_digits(self):
        """Test rejection of non-digit characters."""
        is_valid, error = validate_phone_number("024123456a")
        assert is_valid is False
        assert "only digits" in error.lower()
    
    @pytest.mark.unit
    def test_invalid_local_too_short(self):
        """Test rejection of too-short local format."""
        is_valid, error = validate_phone_number("024123")
        assert is_valid is False
        assert "less than 10 digits" in error.lower()
    
    @pytest.mark.unit
    def test_invalid_local_too_long(self):
        """Test rejection of too-long local format."""
        is_valid, error = validate_phone_number("02412345678901")
        assert is_valid is False
        assert "more than 10 digits" in error.lower()
    
    @pytest.mark.unit
    def test_invalid_international_too_short(self):
        """Test rejection of too-short international format."""
        is_valid, error = validate_phone_number("23324123")
        assert is_valid is False
        assert "less than 12 digits" in error.lower()
    
    @pytest.mark.unit
    def test_invalid_international_too_long(self):
        """Test rejection of too-long international format."""
        is_valid, error = validate_phone_number("2332412345678901")
        assert is_valid is False
        assert "more than 12 digits" in error.lower()


class TestDetectNetwork:
    """Tests for detect_network function."""
    
    @pytest.mark.unit
    def test_mtn_024_prefix(self):
        """Test MTN detection with 024 prefix."""
        assert detect_network("0241234567") == "MTN"
    
    @pytest.mark.unit
    def test_mtn_054_prefix(self):
        """Test MTN detection with 054 prefix."""
        assert detect_network("0541234567") == "MTN"
    
    @pytest.mark.unit
    def test_mtn_055_prefix(self):
        """Test MTN detection with 055 prefix."""
        assert detect_network("0551234567") == "MTN"
    
    @pytest.mark.unit
    def test_mtn_international_format(self):
        """Test MTN detection with international format."""
        assert detect_network("233241234567") == "MTN"
    
    @pytest.mark.unit
    def test_telecel_020_prefix(self):
        """Test TELECEL detection with 020 prefix."""
        assert detect_network("0201234567") == "TELECEL"
    
    @pytest.mark.unit
    def test_telecel_050_prefix(self):
        """Test TELECEL detection with 050 prefix."""
        assert detect_network("0501234567") == "TELECEL"
    
    @pytest.mark.unit
    def test_airteltigo_027_prefix(self):
        """Test AIRTELTIGO detection with 027 prefix."""
        assert detect_network("0271234567") == "AIRTELTIGO"
    
    @pytest.mark.unit
    def test_airteltigo_026_prefix(self):
        """Test AIRTELTIGO detection with 026 prefix."""
        assert detect_network("0261234567") == "AIRTELTIGO"
    
    @pytest.mark.unit
    def test_unknown_network(self):
        """Test unknown network returns None."""
        assert detect_network("0991234567") is None
    
    @pytest.mark.unit
    def test_too_short_number(self):
        """Test too-short number returns None."""
        assert detect_network("02") is None


class TestFormatPhoneForDisplay:
    """Tests for format_phone_for_display function."""
    
    @pytest.mark.unit
    def test_format_international(self):
        """Test formatting international number for display."""
        result = format_phone_for_display("233241234567")
        assert result == "+233 24 123 4567"
    
    @pytest.mark.unit
    def test_format_local_converts_to_international(self):
        """Test local format is converted and formatted."""
        result = format_phone_for_display("0241234567")
        assert result == "+233 24 123 4567"
    
    @pytest.mark.unit
    def test_format_with_plus_sign(self):
        """Test number with plus sign is formatted correctly."""
        result = format_phone_for_display("+233241234567")
        assert result == "+233 24 123 4567"
