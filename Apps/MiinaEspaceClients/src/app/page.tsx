import { LoginForm } from "@/components/LoginForm";

export default function HomePage() {
  return (
    <main className="grid min-h-dvh place-items-center px-4 py-10">
      <div className="w-full max-w-md">
        <LoginForm />
      </div>
    </main>
  );
}
