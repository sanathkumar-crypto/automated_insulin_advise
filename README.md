# Automated Insulin Dose Recommendation System

A comprehensive Python application that provides intelligent insulin dose recommendations based on patient data, GRBS values, and clinical conditions.

## Features

- **Dual Algorithm Support**: IV Insulin Infusion and Basal Bolus algorithms
- **Smart Route Selection**: Automatically determines optimal insulin delivery route
- **RESTful API**: Easy integration with existing healthcare systems
- **Extensive Testing**: Comprehensive test suite with multiple scenarios
- **Console Logging**: Real-time logging to console for monitoring
- **Modular Architecture**: Clean, maintainable code structure (see `STRUCTURE.md`)

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

3. **Run the application**:
   ```bash
   # Option 1: Use the convenience script
   ./run_app.sh
   
   # Option 2: Manual activation
   source .venv/bin/activate
   python app.py
   ```

The application will be available at `http://localhost:5001`

## Deployment to GCP

The service can be deployed to Google Cloud Run as a microservice.

### Quick Deploy

```bash
# Setup (first time only)
cp .env.example .env

# Deploy to production
./deployment/deploy-prod.sh
```

For detailed deployment instructions, see [`deployment/README.md`](deployment/README.md).

## API Usage

### Input Format

Send a POST request to `/recommend` with JSON data. The system supports two input formats:

#### Format 1: Array Format (Recommended)

```json
{
    "GRBS": [180, 200, 190, 185, 175],
    "Insulin": [2, 3, 2.5, 2, 1.5],
    "CKD": false,
    "Dual inotropes": false,
    "route": "sc",
    "diet_order": "NPO"
}
```

**Notes:**
- `GRBS`: Array of up to 5 GRBS values (most recent first). At least one value required.
- `Insulin`: Array of up to 4 previous insulin doses (most recent first). Optional, defaults to 0s.
- Arrays will be padded with zeros if fewer values are provided

#### Format 2: Individual Fields (Backward Compatibility)

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
    "CKD": false,
    "Dual inotropes": false,
    "route": "sc",
    "diet_order": "NPO"
}
```

**Field Descriptions:**
- `GRBS1-5`: Blood glucose readings (mg/dL), most recent first. Only GRBS1 required.
- `Insulin1-4`: Previous insulin doses (IU or IU/hr), most recent first. Optional.
- `CKD`: Chronic Kidney Disease flag (boolean). Default: false
- `Dual inotropes`: Dual inotropes flag (boolean). Default: false
- `route`: Insulin delivery route - "iv" or "sc". Default: "sc"
- `diet_order`: Diet order - "NPO" or "others". Default: "others"

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

The test suite displays real-time test execution logs in the console.

## Logging

The application provides comprehensive console logging:

- **Decision Process**: Which algorithm is selected and why
- **Level Transitions**: When and why levels change
- **Input Validation**: Detailed validation of input data
- **API Requests**: All incoming requests and responses
- **Error Handling**: Detailed error messages and stack traces

All logs are displayed in real-time on the console.

## Code Structure

The application has been refactored from a single 686-line file into a clean, modular architecture:

```
automated_insulin_advise/
├── app.py                          # Flask API server (~100 lines)
│   └── Routes, request/response handling, logging
│
├── engine/                         # Core recommendation engine package
│   ├── __init__.py                # Package initialization
│   ├── config_loader.py           # CSV loading & default configs (~100 lines)
│   ├── validators.py              # Input validation & normalization (~125 lines)
│   ├── algorithms.py              # Algorithm logic & transitions (~175 lines)
│   └── recommendation_engine.py   # Main orchestration (~250 lines)
│
├── algorithm_config.csv            # Algorithm configuration data
└── test_insulin_app.py            # Comprehensive test suite
```

### Module Responsibilities

| Module | Purpose | Key Components |
|--------|---------|----------------|
| `app.py` | Flask API server | Routes, HTTP handling, logging helpers |
| `config_loader.py` | Configuration | Load CSV, parse ranges, defaults |
| `validators.py` | Input validation | Array conversion, sanitization, defaults |
| `algorithms.py` | Algorithm logic | AlgorithmSelector, TransitionRules, DoseFinder, TimingCalculator |
| `recommendation_engine.py` | Orchestration | Main engine, IV/Basal calculations, level matching |

### Data Flow

```
HTTP Request → app.py
    ↓
Input Validation → validators.py
    ↓
Algorithm Selection → algorithms.py
    ↓
Dose Calculation → recommendation_engine.py
    ├→ Level Determination
    ├→ Transition Rules (algorithms.py)
    ├→ Dose Finding (algorithms.py)
    └→ Timing Calculation (algorithms.py)
    ↓
Result → app.py → HTTP Response
```

### Making Changes

| Task | File to Edit |
|------|--------------|
| Add/modify API endpoints | `app.py` |
| Change validation rules | `engine/validators.py` |
| Modify algorithm logic | `engine/algorithms.py` |
| Update dose calculations | `engine/recommendation_engine.py` |
| Change algorithm config | `engine/config_loader.py` or `algorithm_config.csv` |

### Benefits

- ✅ **Readable**: Small, focused files (100-250 lines each)
- ✅ **Maintainable**: Clear separation of concerns
- ✅ **Testable**: Independent, testable modules
- ✅ **Extensible**: Add features without affecting other modules
- ✅ **No circular dependencies**: Clean module imports

## Configuration

No additional configuration is required. The application runs out-of-the-box.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check and API information |
| `/recommend` | POST | Get insulin dose recommendation |

## Error Handling

The application handles various error conditions:

- **Input Validation**: Invalid data types, missing fields, out-of-range values
- **Algorithm Errors**: Invalid algorithm states, calculation errors
- **API Errors**: Malformed requests, server errors

## Security Features

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

### Version 1.2.0
- **Refactored to modular architecture** - Code split into focused modules (686 lines → 5 modules)
- **Removed HTML web interface** (API-only now)
- **Removed Google OAuth authentication** (open access)
- **Simplified logging** to console only (no file logging)
- **Removed test result file generation** (console only)
- **Streamlined dependencies** (Flask + requests only)

### Version 1.1.0
- Added array format for GRBS and Insulin values (recommended format)
- Maintained backward compatibility with individual field format
- Enhanced input validation for array-based inputs

### Version 1.0.0
- Initial release
- IV Insulin Infusion algorithm
- Basal Bolus algorithm
- Comprehensive test suite