from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Role, UserProfile
from .permissions import role_of


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    phone = serializers.CharField(source="profile.phone", required=False, allow_blank=True)
    hometown = serializers.CharField(source="profile.hometown", required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "phone", "hometown", "date_joined"]
        read_only_fields = ["id", "username", "role", "date_joined"]

    def get_role(self, obj):
        return role_of(obj)

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        profile = instance.profile
        for k, v in profile_data.items():
            setattr(profile, k, v)
        profile.save()
        return instance


class RegisterSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]{3,150}$")
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(r"^[0-9+\- ]{7,20}$", required=False, allow_blank=True)

    def validate_username(self, v):
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError("Username already taken.")
        return v

    def validate_email(self, v):
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email already registered.")
        return v.lower()

    def validate(self, attrs):
        password_validation.validate_password(attrs["password"], User(username=attrs["username"], email=attrs["email"]))
        return attrs

    def create(self, data):
        phone = data.pop("phone", "")
        user = User.objects.create_user(**data)  # create_user hashes the password
        user.profile.phone = phone
        user.profile.role = Role.CAMPER  # self-registration is always a camper; admins assign other roles
        user.profile.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=Role.choices, source="profile.role")

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "role", "date_joined"]
        read_only_fields = ["id", "username", "date_joined"]

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if "role" in profile_data:
            UserProfile.objects.filter(user=instance).update(role=profile_data["role"])
        return instance
