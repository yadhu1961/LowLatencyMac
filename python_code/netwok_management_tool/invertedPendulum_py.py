import control # https://pypi.python.org/pypi/control/0.6.6
import scipy.linalg
import sympy
import numpy as np
import math
import matplotlib.pyplot as plt
import socket
import struct
import time
import sys
from threading import Thread


class InvertedPendulum:
    # system model parameters:
    # http://ctms.engin.umich.edu/CTMS/index.php?example=InvertedPendulum&section=SimulinkModeling

    M = 0.5  # mass of the cart
    m = 0.2  # mass of the pendulum
    b = 0.1  # friction coefficient
    I = 0.006  # mass moment of the pendulum
    g = 9.8  # ...
    l = 0.3  # length of the pendulum

    p = I * (M + m) + M * m * math.pow(l, 2)  # helper var

    def __init__(self, sampling_freq):

        # State Space matrices
        self.A = np.matrix([[0, 1, 0, 0],
                       [0, -(self.I + self.m * math.pow(self.l, 2)) * self.b / self.p, (math.pow(self.m, 2) * self.g *
                                                                                        math.pow(self.l, 2)) / self.p, 0],
                       [0, 0, 0, 1],
                       [0, -(self.m * self.l * self.b) / self.p, self.m * self.g * self.l * (self.M + self.m) / self.p, 0]])

        self.B = np.matrix([[0],
                       [(self.I + self.m * math.pow(self.l, 2)) / self.p],
                       [0],
                       [self.m * self.l / self.p]])

        self.C = np.matrix([[1, 0, 0, 0],
                       [0, 0, 1, 0]])

        self.D = np.matrix([[0],
                       [0]])

        # System State Model
        self.sys_ss = control.ss(self.A, self.B, self.C, self.D)
        self.sys_d = control.matlab.c2d(self.sys_ss, 1/sampling_freq)
        self.sampling_freq = sampling_freq

        self.A = self.sys_d.A
        self.B = self.sys_d.B
        self.C = self.sys_d.C
        self.D = self.sys_d.D

        # LQR regulator parameters
        Q = np.dot(np.transpose(self.C), self.C)
        Q[0, 0] = 5000
        Q[2, 2] = 1000
        R = np.matrix([[1]])

        # Discrete LQR Control Gain
        self.K = InvertedPendulum.dlqr(self.A, self.B, Q, R)[0]
        self.Q = Q
        self.R = R

        self.state_transition_matrix(self.sys_ss.A, self.sys_ss.B)

        # Pre-compensator
        self.N_bar = -61.55

    @staticmethod
    def dlqr(A, B, Q, R):
        """
        Solve the discrete time lqr controller.
        x[k+1] = A x[k] + B u[k]
        cost = sum x[k].T*Q*x[k] + u[k].T*R*u[k]

        References:
        LQR controller: https://en.wikipedia.org/wiki/Linear%E2%80%93quadratic_regulator
        http://ctms.engin.umich.edu/CTMS/index.php?example=InvertedPendulum&section=ControlDigital

        """

        # first, try to solve the ricatti equation
        X = np.matrix(scipy.linalg.solve_discrete_are(A, B, Q, R))

        # compute the LQR gain
        K = np.matrix(scipy.linalg.inv(B.T * X * B + R) * (B.T * X * A))

        eigVals, eigVecs = scipy.linalg.eig(A - B * K)

        return K, X, eigVals

    def state_transition_matrix(self, A, B):

        t = sympy.symbols('t')

        eigVals, eigVecs = scipy.linalg.eig(A)

        g = np.diag(np.e**(eigVals*t))
        phi = eigVecs*g*scipy.linalg.inv(eigVecs)
        x0 = np.matrix([[0.2], [0.2], [0.2], [0.2]])
        x = phi*x0

        # a = 1
        # f = np.e**t
        # y = f.evalf(subs={t: a})

        # f = sympy.lambdify(t, np.e**t, "numpy")

        f = sympy.lambdify(t, x[2, 0], "numpy")
        a = np.linspace(0, 1, 1e3)
        f_evd = f(a)
        #
        plt.figure()
        plt.plot(a, f_evd)

        print("Ciao!")





    def sense(self, x):
        """
        Retrieve the up-to-date state variables of the plant
        :param x: state variables
        :return:
        """
        sensed_x = x
        return sensed_x

    def control(self, r, x):
        """
        # Compute the control value u fom the system variables x and the external reference
        :param r: external reference
        :param x: state variables
        :return:
        """
        # Pre-compensator
        u = np.dot(self.N_bar, np.matrix(r)) - np.dot(self.K, x)

        # No pre-compensator
        # u = np.matrix(r) - np.dot(self.K, x)
        return u

    def actuate(self, x, u):
        """
        Compute the evolution of the state variables applying the control value
        :param x: state variables
        :param u: control value
        :return:
        """
        x = np.dot(self.A, x) + np.dot(self.B, u) + np.random.normal(0, 0.001, size=(4,1))
        return x

    def estimate(self, last_x, last_u):
        """
        Perform an estimation of the plant evolution based on the last state values and the last control value
        :param last_x: last state variables
        :param last_u: last control value
        :return:
        """
        x_est = np.dot(self.A, last_x) + np.dot(self.B, last_u)
        return x_est

    def simulate(self, sim_start, sim_end):
        sampling_period = 1/self.sampling_freq
        time_steps = np.arange(sim_start, sim_end + sampling_period, sampling_period)

        # Plant reference values over time
        r = 0.2 * np.ones(shape=time_steps.shape)  # Constant
        # r = 0.2 * np.sin(2*np.pi*time_steps)  # Sinusoidal

        k_min = 0
        k_max = len(time_steps)

        x = np.zeros(shape=(self.A.shape[0], 1))
        received_x = np.zeros(shape=(self.A.shape[0], 1))

        y = np.zeros(shape=(self.C.shape[0], 1))

        u = np.zeros((1, 1))
        received_u = np.zeros((1,1))

        x_out = np.zeros(shape=(self.A.shape[0], len(time_steps)))
        y_out = np.zeros(shape=(self.C.shape[0], len(time_steps)))
        u_out = np.zeros(shape=(1, len(time_steps)))

        x[:] = np.dot(self.A, x)

        for k in range(k_min, k_max):

            # Store values from previous iteration, used for plotting
            y_out[:, k] = y[:, 0]
            x_out[:, k] = x[:, 0]
            u_out[:, k] = u[:, 0]

            # Sensor block
            sensed_x = self.sense(x)

            # Transmission of the current states to the controller (send sensed_x)
            if np.random.binomial(1, 1):
                received_x = sensed_x
            else:
                # received_x = np.reshape(x_out[:, k-1], (self.A.shape[0], 1))
                received_x[:] = self.estimate(np.reshape(x_out[:, k-1], (self.A.shape[0], 1)),
                                              np.reshape(u_out[:, k-1], (1, 1)))

            # Control block
            u = self.control(r[k], received_x)

            # Transmission of the control value to the actuator (send u)
            if np.random.binomial(1, 1):
                received_u = u
            else:
                received_u[:] = u_out[:, k-1]

            u[:] = received_u

            # Actuator block
            x[:] = self.actuate(x, received_u)

            # Plant output
            y[:] = np.dot(self.C, x)

        return time_steps, y_out


class InvertedPendulumPlant(InvertedPendulum):
    def __init__(self, f):
        InvertedPendulum.__init__(self, f)
        self.sensor_socket = MyUDPSocket(is_robot=1, is_tx=1)
        self.actuator_socket = MyUDPSocket(is_robot=1, is_tx=0)

    def run(self):
        print("Starting Plant")

        t0 = Thread(target=self.actuator_socket.receive)
        t1 = Thread(target=self.control_loop)

        t0.daemon = True
        t1.daemon = True

        try:
            t0.start()
            t1.start()
            while True:
                time.sleep(100)
        except (KeyboardInterrupt, SystemExit):
            print('\n! Received keyboard interrupt, quitting threads.\n')
            return

    def control_loop(self):
        sampling_period = 1/self.sampling_freq

        # Plant reference value
        r = 0.2  # Constant

        x = np.zeros(shape=(self.A.shape[0], 1))
        y = np.zeros(shape=(self.C.shape[0], 1))
        u = np.zeros((1, 1))
        received_u = np.zeros((1,1))

        x[:] = np.dot(self.A, x)

        k = 0
        while True:

            # Transmission of the current states to the controller (send sensed_x)
            self.sensor_socket.send(x)

            received = False
            if len(self.actuator_socket.rx_queue) is not 0:
                u_rx = self.actuator_socket.rx_queue.pop()
                received = True
            else:
                print("%d: No control command, no control applied" % k)
                received = False

            # Transmission of the control value to the actuator (send u)
            if received is False:
                u_rx = np.zeros((1, 1))
                # u_rx[:] = u_out[:, k-1]
                u_rx = self.control(r,x)
            else:
                print("%d: Control command received: %f" % (k,u_rx))

            u[:] = u_rx

            # Actuator block
            x[:] = self.actuate(x, u)

            # Plant output
            y[:] = np.dot(self.C, x)

            k += 1
            time.sleep(sampling_period)


class InvertedPendulumController(InvertedPendulum):
    def __init__(self, f):
        InvertedPendulum.__init__(self, f)
        self.controller_socket = MyUDPSocket(is_robot=0)

    def run(self):
        print("Starting Controller")

        t0 = Thread(target=self.controller_socket.receive)
        t1 = Thread(target=self.control_loop)

        t0.daemon = True
        t1.daemon = True

        try:
            t0.start()
            t1.start()
            while True:
                time.sleep(100)
        except (KeyboardInterrupt, SystemExit):
            print('\n! Received keyboard interrupt, quitting threads.\n')
            return

    def control_loop(self):
        sampling_period = 1 / self.sampling_freq

        # Plant reference value
        r = 0.2  # Constant

        x = np.zeros(shape=(self.A.shape[0], 1))
        x_rx = np.zeros(shape=(self.A.shape[0], 1))
        y = np.zeros(shape=(self.C.shape[0], 1))
        u = np.zeros((1, 1))

        x_prev = np.zeros(shape=(self.A.shape[0], 1))

        x[:] = np.dot(self.A, x)

        k = 0
        while True:
            received = False
            if len(self.controller_socket.rx_queue) is not 0:
                x_rx = self.controller_socket.rx_queue.pop()
                received = True
            else:
                received = False

            if received is False:
                print("%d : No states received, estimate" % k)
                # received_x = np.reshape(x_out[:, k-1], (self.A.shape[0], 1))
                x_rx[:] = self.actuate(x_prev, u)
            else:
                print("%d : Received states: %f, %f, %f, %f" % (k, x_rx[0, 0], x_rx[1, 0], x_rx[2, 0], x_rx[3, 0]))

            # Control block
            u = self.control(r, x_rx)

            # Transmission of the control value to the actuator (send u)
            self.controller_socket.send(u)   # WARNING: assumption that the packet was received

            # Actuator block
            x_prev[:] = x[:]
            x[:] = self.actuate(x, u)

            # Plant output
            y[:] = np.dot(self.C, x)

            k += 1
            time.sleep(sampling_period)


class MyUDPSocket:
    """
    UDP socket between the Inverted Pendulum (Robot) and the Controller
    """
    # - - - Connection settings - - - #
    CON_CONTROL_IP = '127.0.0.1'  # Control IP-address
    CON_CONTROL_PORT = 8888  # Control port
    CON_ROBOT_IP = '127.0.0.1'  # Robot IP-address
    CON_ROBOT_PORT_S = 8887  # Robot sensing port
    CON_ROBOT_PORT_A = 8889  # Robot actuation port

    MAX_QUEUE_LEN = 10

    def __init__(self, is_robot, is_tx=0, queue=None):
        self.is_tx = is_tx
        self.is_robot = is_robot
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if queue is None:
            queue = []
        self.rx_queue = queue

        if self.is_robot:
            if self.is_tx:
                self.sock.setblocking(0)
                self.sock.bind((MyUDPSocket.CON_ROBOT_IP, MyUDPSocket.CON_ROBOT_PORT_S))
            else:
                self.sock.setblocking(1)
                self.sock.bind((MyUDPSocket.CON_ROBOT_IP, MyUDPSocket.CON_ROBOT_PORT_A))
        else:
            self.sock.setblocking(1)
            self.sock.bind((MyUDPSocket.CON_CONTROL_IP, MyUDPSocket.CON_CONTROL_PORT))

    def receive(self):
        try:
            if self.is_robot:
                while True:
                    recv = self.sock.recvfrom(H2R_PACKET_SIZE)
                    if len(recv[0]) is H2R_PACKET_SIZE:
                        data = struct.unpack(H2R_PACKET_FORMAT, recv[0])
                        control_command = data[H2R_PACKET_VARS.control_command]
                        self.rx_queue.append(control_command)
                        if len(self.rx_queue) > self.MAX_QUEUE_LEN:
                            discard = self.rx_queue.pop(0)
                            print("Buffer full, dropping packet: ")
                            print(discard)
            else:
                while True:
                    x = np.zeros(shape=(R2H_PACKET_SIZE / len(R2H_PACKET_FORMAT), 1))
                    recv = self.sock.recvfrom(R2H_PACKET_SIZE)
                    if len(recv[0]) is R2H_PACKET_SIZE:
                        data = struct.unpack(R2H_PACKET_FORMAT, recv[0])
                        x[0, 0] = data[R2H_PACKET_VARS.P_angle]
                        x[1, 0] = data[R2H_PACKET_VARS.P_speed]
                        x[2, 0] = data[R2H_PACKET_VARS.C_position]
                        x[3, 0] = data[R2H_PACKET_VARS.C_speed]
                        self.rx_queue.append(x)
                        if len(self.rx_queue) > self.MAX_QUEUE_LEN:
                            drop = self.rx_queue.pop(0)
                            print("Buffer full, dropping packet: %f, %f, %f, %f" %
                                  (drop[0, 0], drop[1, 0], drop[2, 0], drop[3, 0]))

        except socket.timeout:
            print ('Rx timeout, is_robot = %d' % self.is_robot)
        except socket.error:
            print ('Rx error, is_robot = %d' % self.is_robot)
        except (KeyboardInterrupt, IndexError) as e:
            self.sock.close()

    def send(self, data):
        try:
            if self.is_robot:
                send_data = [0] * len(R2H_PACKET_FORMAT)
                send_data[R2H_PACKET_VARS.P_angle] = data[0, 0]
                send_data[R2H_PACKET_VARS.P_speed] = data[1, 0]
                send_data[R2H_PACKET_VARS.C_position] = data[2, 0]
                send_data[R2H_PACKET_VARS.C_speed] = data[3, 0]
                self.sock.sendto(struct.pack(R2H_PACKET_FORMAT, *send_data),
                                 (self.CON_CONTROL_IP, self.CON_CONTROL_PORT))
            else:
                send_data = [0] * len(H2R_PACKET_FORMAT)
                send_data[H2R_PACKET_VARS.control_command] = data
                self.sock.sendto(struct.pack(H2R_PACKET_FORMAT, *send_data),
                                 (self.CON_ROBOT_IP, self.CON_ROBOT_PORT_A))
        except socket.error:
            print ('Tx error, is_robot = %d' % self.is_robot)
        return


H2R_RATE = 1 / 0.01
H2R_PACKET_FORMAT = 'f'
H2R_PACKET_SIZE = struct.calcsize(H2R_PACKET_FORMAT)
class H2R_PACKET_VARS:
    control_command = 0

R2H_PACKET_FORMAT = 'ffff'
R2H_PACKET_SIZE = struct.calcsize(R2H_PACKET_FORMAT)
class R2H_PACKET_VARS:
    P_angle = 0
    P_speed = 1
    C_position = 2
    C_speed = 3


if __name__ == "__main__":

    f = 100.0  # 40 Hz
    T = 1/f  # 8 ms

    print(sys.argv[1:])
    if sys.argv[1] is "p":
        inv_pend = InvertedPendulumPlant(f)
        inv_pend.run()

    if sys.argv[1] is "c":
        controller = InvertedPendulumController(f)
        controller.run()

    if sys.argv[1] is "s":
        inv_pend = InvertedPendulum(f)
        t_out, y_out = inv_pend.simulate(0, 20)

        fig, ax1 = plt.subplots()
        ax1.set_title('Plant evolution with Digital LQR Control and Pre-compensation')
        ax1.plot(t_out, y_out[0, :], 'b-')
        ax1.set_xlabel('time (s)')
        ax1.set_ylabel('cart position (m)', color='b')
        for tl in ax1.get_yticklabels():
            tl.set_color('b')

        ax2 = ax1.twinx()
        ax2.plot(t_out, y_out[1, :], 'g-')
        ax2.set_ylabel('pendulum angle (radians)', color='g')
        for tl in ax2.get_yticklabels():
            tl.set_color('g')

        plt.grid()
        plt.show()
