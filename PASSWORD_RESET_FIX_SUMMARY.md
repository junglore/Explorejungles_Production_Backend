# Password Reset OTP Verification Fix

## Issue Summary
The forgot password OTP verification was failing while signup OTP verification was working properly. The root cause was a timezone handling mismatch between the stored expiration times and comparison logic.

## Root Cause Analysis

### The Problem
1. **User Model**: Uses `DateTime(timezone=True)` for `password_reset_expires` and `email_verification_expires`
2. **TempUserRegistration Model**: Uses `DateTime` (timezone-naive) for `email_verification_expires`
3. **Email Service**: Was using `datetime.utcnow()` inconsistently for both timezone-aware and timezone-naive comparisons

### Why Signup Worked But Password Reset Didn't
- **Signup OTP**: Uses `TempUserRegistration` model with timezone-naive `DateTime`
- **Password Reset OTP**: Uses `User` model with timezone-aware `DateTime(timezone=True)`
- When SQLAlchemy stores/retrieves timezone-aware fields, it converts them appropriately
- The comparison logic was mixing timezone-naive and timezone-aware datetime objects

## Changes Made

### 1. Fixed `send_password_reset_email()` function
**Before:**
```python
expires_at = datetime.utcnow() + timedelta(minutes=15)
```

**After:**
```python
expires_at = datetime.utcnow().replace(tzinfo=None) + timedelta(minutes=15)
```

### 2. Enhanced `verify_password_reset_otp()` function
**Before:**
```python
current_time = datetime.utcnow()
```

**After:**
```python
current_time = datetime.utcnow().replace(tzinfo=None)
# Added debug logging
logger.info(f"Password reset OTP verification for {user_email}: current_time={current_time}, expires_time={expires_time}, otp_match={user.password_reset_token == otp}")
# Added detailed error logging
logger.warning(f"Password reset OTP verification failed for {user_email}: OTP={otp}, stored_token={user.password_reset_token}, expired={(expires_time <= current_time) if expires_time else 'No expiry set'}")
```

### 3. Applied consistent fixes to email verification functions
- `send_verification_email()`: Fixed timezone handling
- `verify_email_otp()`: Added debug logging and consistent timezone handling
- `verify_temp_user_otp()`: Added debug logging for consistency

### 4. Added comprehensive debug logging
- Added timestamp comparison logging
- Added OTP matching verification
- Added detailed error messages for failed verifications

## Key Technical Details

### Timezone Strategy
- **Database Storage**: All datetime fields use timezone-naive storage (SQLAlchemy converts timezone-aware to UTC when storing)
- **Comparison Logic**: All comparisons now use timezone-naive datetime objects
- **Consistency**: Using `.replace(tzinfo=None)` to ensure timezone-naive datetime objects

### Debug Logging
Added logging that shows:
- Current time vs expiration time
- OTP matching status
- Detailed failure reasons

## Testing

### Manual Testing Steps
1. Run the backend server
2. Use the provided test script: `python test_password_reset_fix.py`
3. Test with a real email address
4. Check email for OTP
5. Verify OTP verification works

### Expected Behavior
- Password reset emails should be sent successfully
- OTP verification should work within the 15-minute window
- Expired OTPs should be properly rejected
- Clear error messages for debugging

## Files Modified
1. `app/services/email_service.py` - Core fix for timezone handling
2. `test_password_reset_fix.py` - Test script for verification

## Verification Checklist
- [ ] Signup OTP verification still works
- [ ] Password reset OTP verification now works
- [ ] Email verification OTP works
- [ ] Expired OTPs are properly rejected
- [ ] Debug logs provide clear information
- [ ] No timezone-related errors in logs

## Future Improvements
1. Consider migrating database schema to use consistent timezone handling
2. Add automated tests for OTP flows
3. Consider using UTC timestamps throughout the application
4. Add OTP rate limiting for security

## Notes
- The fix maintains backward compatibility
- No database schema changes required
- Existing tokens will continue to work
- The 15-minute expiration window remains unchanged
