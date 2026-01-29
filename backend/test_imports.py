try:
    print("Importing models...")
    import models
    print("Importing models_alpha...")
    import models_alpha
    print("Importing models_ml...")
    import models_ml
    print("All imports successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
