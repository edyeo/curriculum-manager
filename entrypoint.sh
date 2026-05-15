#!/bin/sh
case "$AGENT" in
  curriculum-manager)
    exec uvicorn apps.curriculum_manager.main:app --host 0.0.0.0 --port ${PORT:-8001}
    ;;
  mental-model-manager)
    exec uvicorn apps.mental_model_manager.main:app --host 0.0.0.0 --port ${PORT:-8002}
    ;;
  researcher)
    exec uvicorn apps.researcher.main:app --host 0.0.0.0 --port ${PORT:-8003}
    ;;
  question-generator)
    exec uvicorn apps.question_generator.main:app --host 0.0.0.0 --port ${PORT:-8004}
    ;;
  gateway)
    exec uvicorn apps.gateway:app --host 0.0.0.0 --port ${PORT:-9000}
    ;;
  *)
    echo "Unknown AGENT: $AGENT"
    exit 1
    ;;
esac
