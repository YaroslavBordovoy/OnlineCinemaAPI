import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    Text,
    DECIMAL,
    UniqueConstraint,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Enum as SQLAlchemyEnum

from database.models.accounts import UserModel
from database.models.base import Base


class ReactionEnum(str, Enum):
    LIKE = "Like"
    DISLIKE = "Dislike"


MoviesGenresModel = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


MoviesStarsModel = Table(
    "movies_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


MoviesDirectorsModel = Table(
    "movies_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class ReactionModel(Base):
    __tablename__ = "reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    reaction: Mapped[ReactionEnum] = mapped_column(
        SQLAlchemyEnum(ReactionEnum), nullable=True
    )

    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="reactions")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="reactions")


class CommentModel(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    comment: Mapped[str] = mapped_column(Text, nullable=True)

    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="reactions")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="reactions")


class FavoriteModel(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    favorite: Mapped[bool] = mapped_column(Boolean, nullable=True)

    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id"), nullable=False)
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="reactions")

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="reactions")


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel", secondary=MoviesGenresModel, back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel", secondary=MoviesStarsModel, back_populates="stars"
    )

    def __repr__(self):
        return f"<Star(name='{self.name}')>"


class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesDirectorsModel,
        back_populates="directors",
    )

    def __repr__(self):
        return f"<Director(name='{self.name}')>"


class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel", back_populates="certification"
    )

    def __repr__(self):
        return f"<Certification(name='{self.name}')>"


class MovieModel(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float] = mapped_column(Float, nullable=True)
    gross: Mapped[float] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    reaction: Mapped["ReactionModel"] = relationship("ReactionModel", back_populates="movie", uselist=False, default_factory=None)
    comment: Mapped["CommentModel"] = relationship("CommentModel", back_populates="movie", uselist=False, default_factory=None)
    favorite: Mapped["FavoriteModel"] = relationship("FavoriteModel", back_populates="movie", uselist=False, default_factory=None)

    certification_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("certifications.id"), nullable=False
    )
    certification: Mapped["CertificationModel"] = relationship(
        "CertificationModel", back_populates="movies"
    )

    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel", secondary=MoviesGenresModel, back_populates="movies"
    )

    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel",
        secondary=MoviesDirectorsModel,
        back_populates="movies",
    )

    stars: Mapped[list["StarModel"]] = relationship(
        "StarModel", secondary=MoviesStarsModel, back_populates="movies"
    )

    __table_args__ = (
        UniqueConstraint(
            "name", "year", "time", name="unique_movie_constraint"
        ),
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self):
        return (
            f"<Movie("
            f"name='{self.name}', "
            f"release_year='{self.year}', "
            f"duration='{self.time}', "
            f"IMDB_score={self.imdb}"
            f")>"
        )
