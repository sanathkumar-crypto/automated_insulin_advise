# Automated Insulin Dose Recommendation System

A comprehensive Python application that provides intelligent insulin dose recommendations based on patient data, GRBS values, and clinical conditions.

## Features

- **Dual Algorithm Support**: IV Insulin Infusion and Basal Bolus algorithms
- **Smart Route Selection**: Automatically determines optimal insulin delivery route
- **Gmail OAuth Authentication**: Secure access restricted to @cloudphysician.net domain
- **Comprehensive Logging**: Detailed decision-making process documentation
- **RESTful API**: Easy integration with existing healthcare systems
- **Extensive Testing**: Comprehensive test suite with multiple scenarios

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd automated_insulin_advise
   ```

2. **Run the setup script**:
   ```bash
   python3 setup.py
   ```
   This will:
   - Create a virtual environment
   - Install all required dependencies
   - Set up environment variables
   - Create necessary directories

3. **Configure Google OAuth**:
   - Update the `.env` file with your Google OAuth credentials
   - Get credentials from [Google Cloud Console](https://console.cloud.google.com/)

4. **Run the application**:
   ```bash
   # Option 1: Use the convenience script
   ./run_app.sh
   
   # Option 2: Manual activation
   source venv/bin/activate
   python app.py
   ```

The application will be available at `http://localhost:5000`

## API Usage

### Authentication

The application uses Gmail OAuth for authentication. Only users with @cloudphysician.net email addresses are authorized to access the system.

### Input Format

Send a POST request to `/recommend` with the following JSON structure:

```json
{
    "GRBS1": 180,
    "GRBS2": 200,
    "GRBS3": 190,
    "GRBS4": 185,
    "GRBS5": 175,
    "Insulin1": 2,
    "Insulin2": 3,
    "Insulin3": 2.5,
    "Insulin4": 2,
    "Insulin5": 1.5,
    "CKD": false,
    "Dual inotropes": false,
    "route": "sc",
    "diet_order": "NPO"
}
```

### Output Format

The API returns a JSON response with the recommendation:

```json
{
    "Suggested_insulin_dose": 4,
    "Suggested_route": "subcutaneous",
    "next_grbs_after": 4,
    "algorithm_used": "Basal Bolus",
    "level": 3,
    "action": "Medium dose"
}
```

## Algorithm Logic

### Route Selection

The system automatically determines the appropriate algorithm based on:

1. **IV Insulin Infusion Algorithm** is used when:
   - Route is SC AND (dual_inotropes = false OR GRBS1 & GRBS2 > 350)
   - Route is IV AND not all GRBS1-4 are in 150-180 mg/dL range

2. **Basal Bolus Algorithm** is used for all other cases

### IV Insulin Infusion Algorithm

- **Starting Level**: 2
- **Dose Units**: IU/hr
- **Level Transitions**:
  - **Move Up**: Blood glucose > 150 mg/dL AND (increased OR decreased 0-60 mg/dL)
  - **Move Down**: Blood glucose < 110 mg/dL
  - **Maintain**: Blood glucose 110-150 mg/dL OR decreased by 61+ mg/dL

### Basal Bolus Algorithm

- **Starting Level**: 2
- **Dose Units**: IU
- **Level Transitions**:
  - **Move Up**: 2+ readings above 180 mg/dL
  - **Move Down**: Any reading below 140 mg/dL

### Next GRBS Check Timing

- **IV Route**: Hourly (or 2nd hourly if GRBS1-4 are 140-180 mg/dL)
- **SC Route + NPO**: 4th hourly
- **SC Route + Others**: 6th hourly

## Testing

### Running the Test Suite

1. **Start the Flask application**:
   ```bash
   python app.py
   ```

2. **Run the test suite** (in a new terminal):
   ```bash
   python test_insulin_app.py
   ```

### Test Coverage

The test suite includes:

- **IV Algorithm Scenarios**: High GRBS, route switching, dual inotropes conditions
- **Basal Bolus Scenarios**: Normal SC routes, level transitions
- **Edge Cases**: Invalid inputs, missing fields, extreme values
- **Algorithm Transitions**: Level up/down scenarios
- **Timing Scenarios**: Different check intervals

### Test Output

The test suite generates:
- **Console Output**: Real-time test execution logs
- **test_results.log**: Detailed logging of all test scenarios
- **test_results.json**: Structured test results for analysis

## Logging

The application provides comprehensive logging:

- **Decision Process**: Which algorithm is selected and why
- **Level Transitions**: When and why levels change
- **Input Validation**: Detailed validation of input data
- **API Requests**: All incoming requests and responses
- **Error Handling**: Detailed error messages and stack traces

Log files:
- `insulin_recommendations.log`: Main application logs
- `test_results.log`: Test execution logs

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | Yes |
| `SECRET_KEY` | Flask secret key | Yes |

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `http://localhost:5000/login/authorized`
6. Copy Client ID and Secret to environment variables

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page with API documentation |
| `/login` | GET | Initiate Gmail OAuth login |
| `/login/authorized` | GET | OAuth callback handler |
| `/recommend` | POST | Get insulin dose recommendation |
| `/logout` | GET | Logout user |

## Error Handling

The application handles various error conditions:

- **Input Validation**: Invalid data types, missing fields, out-of-range values
- **Authentication**: Unauthorized email domains, OAuth failures
- **Algorithm Errors**: Invalid algorithm states, calculation errors
- **API Errors**: Malformed requests, server errors

## Security Features

- **Domain Restriction**: Only @cloudphysician.net emails allowed
- **OAuth Authentication**: Secure Google OAuth 2.0 flow
- **Input Validation**: Comprehensive input sanitization
- **Error Handling**: Secure error messages without sensitive data exposure

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact the development team or create an issue in the repository.

## Changelog

### Version 1.0.0
- Initial release
- IV Insulin Infusion algorithm
- Basal Bolus algorithm
- Gmail OAuth authentication
- Comprehensive test suite
- Detailed logging system