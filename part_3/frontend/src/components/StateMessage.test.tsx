import { render, screen } from "@testing-library/react";
import { StateMessage } from "@/components/StateMessage";

test("renders loading, error, and empty states", () => {
  const { rerender } = render(<StateMessage status="loading" />);
  expect(screen.getByText(/Loading data/i)).toBeInTheDocument();

  rerender(<StateMessage status="error" errorText="Backend failed" />);
  expect(screen.getByRole("alert")).toHaveTextContent("Backend failed");

  rerender(<StateMessage status="success" isEmpty emptyText="Nothing here" />);
  expect(screen.getByText("Nothing here")).toBeInTheDocument();
});
