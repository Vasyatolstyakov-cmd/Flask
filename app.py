import os
from pathlib import Path

from flask import Flask, current_app, jsonify, request
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import scoped_session, sessionmaker

from models import Advertisement, Base


EDITABLE_FIELDS = {"title", "description", "owner"}


def error_response(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def validate_advertisement(data, *, partial: bool = False):
    if not isinstance(data, dict):
        return None, "request body must be a JSON object"

    unknown_fields = set(data) - EDITABLE_FIELDS
    if unknown_fields:
        fields = ", ".join(sorted(unknown_fields))
        return None, f"unknown fields: {fields}"

    if not partial:
        missing_fields = EDITABLE_FIELDS - set(data)
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            return None, f"missing fields: {fields}"
    elif not data:
        return None, "at least one editable field is required"

    cleaned = {}
    for field in EDITABLE_FIELDS & set(data):
        value = data[field]
        if not isinstance(value, str) or not value.strip():
            return None, f"field '{field}' must be a non-empty string"
        cleaned[field] = value.strip()

    if len(cleaned.get("title", "")) > 200:
        return None, "field 'title' must contain no more than 200 characters"
    if len(cleaned.get("owner", "")) > 120:
        return None, "field 'owner' must contain no more than 120 characters"

    return cleaned, None


def get_session():
    return current_app.extensions["db_session"]()


def create_app(database_url: str | None = None, *, testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = testing

    default_database = Path(__file__).with_name("advertisements.db")
    database_url = database_url or os.getenv(
        "DATABASE_URL", f"sqlite:///{default_database}"
    )

    engine_options = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_options)
    db_session = scoped_session(
        sessionmaker(bind=engine, expire_on_commit=False)
    )
    Base.metadata.create_all(engine)

    app.extensions["db_engine"] = engine
    app.extensions["db_session"] = db_session

    @app.teardown_appcontext
    def remove_session(_exception=None):
        db_session.remove()

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": "advertisements-api",
                "endpoints": {
                    "create": "POST /advertisements",
                    "list": "GET /advertisements",
                    "get": "GET /advertisements/<id>",
                    "edit": "PATCH or PUT /advertisements/<id>",
                    "delete": "DELETE /advertisements/<id>",
                },
            }
        )

    @app.post("/advertisements")
    def create_advertisement():
        data, validation_error = validate_advertisement(
            request.get_json(silent=True)
        )
        if validation_error:
            return error_response(validation_error, 400)

        advertisement = Advertisement(**data)
        session = get_session()
        try:
            session.add(advertisement)
            session.commit()
            return jsonify(advertisement.to_dict()), 201
        except SQLAlchemyError:
            session.rollback()
            current_app.logger.exception("failed to create advertisement")
            return error_response("database error", 500)
        finally:
            session.close()

    @app.get("/advertisements")
    def list_advertisements():
        session = get_session()
        try:
            advertisements = session.scalars(
                select(Advertisement).order_by(Advertisement.id)
            ).all()
            return jsonify([item.to_dict() for item in advertisements])
        finally:
            session.close()

    @app.get("/advertisements/<int:advertisement_id>")
    def get_advertisement(advertisement_id: int):
        session = get_session()
        try:
            advertisement = session.get(Advertisement, advertisement_id)
            if advertisement is None:
                return error_response("advertisement not found", 404)
            return jsonify(advertisement.to_dict())
        finally:
            session.close()

    @app.route(
        "/advertisements/<int:advertisement_id>", methods=["PATCH", "PUT"]
    )
    def edit_advertisement(advertisement_id: int):
        partial = request.method == "PATCH"
        data, validation_error = validate_advertisement(
            request.get_json(silent=True), partial=partial
        )
        if validation_error:
            return error_response(validation_error, 400)

        session = get_session()
        try:
            advertisement = session.get(Advertisement, advertisement_id)
            if advertisement is None:
                return error_response("advertisement not found", 404)

            for field, value in data.items():
                setattr(advertisement, field, value)
            session.commit()
            return jsonify(advertisement.to_dict())
        except SQLAlchemyError:
            session.rollback()
            current_app.logger.exception("failed to edit advertisement")
            return error_response("database error", 500)
        finally:
            session.close()

    @app.delete("/advertisements/<int:advertisement_id>")
    def delete_advertisement(advertisement_id: int):
        session = get_session()
        try:
            advertisement = session.get(Advertisement, advertisement_id)
            if advertisement is None:
                return error_response("advertisement not found", 404)

            session.delete(advertisement)
            session.commit()
            return "", 204
        except SQLAlchemyError:
            session.rollback()
            current_app.logger.exception("failed to delete advertisement")
            return error_response("database error", 500)
        finally:
            session.close()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
