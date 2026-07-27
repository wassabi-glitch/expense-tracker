import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export type UserResponse = {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  has_local_password: boolean;
  is_premium: boolean;
};

export function useUserQuery() {
  return useQuery<UserResponse, Error>({
    queryKey: ['user'],
    queryFn: async () => {
      const response = await apiClient.get<UserResponse>('/users/me');
      return response.data;
    },
  });
}
