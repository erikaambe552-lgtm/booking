from django.contrib.auth.models import User
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .permissions import IsSystemAdmin
from .serializers import AdminUserSerializer, LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        token, _ = Token.objects.get_or_create(user=s.validated_data["user"])
        return Response({"token": token.key, "user": UserSerializer(s.validated_data["user"]).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()  # invalidate the token server-side
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class AdminUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsSystemAdmin]
    serializer_class = AdminUserSerializer
    queryset = User.objects.select_related("profile").order_by("id")

    def perform_destroy(self, instance):
        # Soft-disable instead of deleting so reservation history stays intact.
        instance.is_active = False
        instance.save(update_fields=["is_active"])
