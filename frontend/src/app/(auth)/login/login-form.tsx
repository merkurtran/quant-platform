"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/stores/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const loginSchema = z.object({
  email: z.string().email("请输入有效的邮箱"),
  password: z.string().min(1, "请输入密码"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({ resolver: zodResolver(loginSchema) });

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true);
    try {
      const response = await authService.login(data);
      setAuth(response);
      toast.success("登录成功");
      router.replace("/market");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p className="text-xs font-medium text-black/50">QUANT WORKSPACE</p>
      <h2 className="mt-3 text-3xl font-light">欢迎回来</h2>
      <p className="mt-2 text-sm text-black/55">继续查看行情、策略与模拟交易。</p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-5">
        <div className="space-y-2">
          <Label htmlFor="email" className="text-xs text-black/70">邮箱</Label>
          <Input id="email" type="email" autoComplete="email" placeholder="user@example.com" className="border-black/15 bg-white focus-visible:border-black focus-visible:ring-black/10" {...register("email")} />
          {errors.email && <p className="text-xs text-danger">{errors.email.message}</p>}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className="text-xs text-black/70">密码</Label>
          <div className="relative">
            <Input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="请输入密码" className="border-black/15 bg-white pr-10 focus-visible:border-black focus-visible:ring-black/10" {...register("password")} />
            <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-1 top-1 flex h-8 w-8 items-center justify-center rounded-full text-black/45 hover:bg-black/5 hover:text-black" aria-label={showPassword ? "隐藏密码" : "显示密码"}>
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && <p className="text-xs text-danger">{errors.password.message}</p>}
        </div>

        <Button type="submit" className="h-11 w-full rounded-full bg-black text-white hover:bg-black/85" disabled={loading}>
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          登录平台
        </Button>

        <p className="text-center text-sm text-black/55">
          还没有账号？ <Link href="/register" className="font-medium text-black underline-offset-4 hover:underline">创建账号</Link>
        </p>
      </form>
    </div>
  );
}
