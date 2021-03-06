# This is a very simple implementation of the UCT Monte Carlo Tree Search algorithm in Python 2.7.
# The function UCT(rootstate, itermax, verbose = False) is towards the bottom of the code.
# It aims to have the clearest and simplest possible code, and for the sake of clarity, the code is orders of magnitude less efficient than it could be made, particularly by using a state.GetRandomMove() or state.DoRandomRollout() function.
#
# Example GameState classes for Nim, OXO and Othello are included to give some idea of how you can write your own GameState use UCT in your 2-player game. Change the game to be played in the UCTPlayGame() function at the bottom of the code.
#
# Written by Peter Cowling, Ed Powley, Daniel Whitehouse (University of York, UK) September 2012.
#
# Licence is granted to freely use and distribute for any sensible/legal purpose so long as this comment remains in any distributed code.
#
# For more information about Monte Carlo Tree Search check out our web site at www.mcts.ai

from board import Board

import numpy as np
import random
import math
import os
import sys
import time
import copy


#------------------------------------------------------------
# Environment
#------------------------------------------------------------
class Env(object):
	def __init__(self):
		self.grid_size = 10
		self.state_size = self.grid_size * self.grid_size
		'''
			board, state 묶어버리자
		'''
		# board는 object 내부에서 오목의 연산 처리용으로만 사용한다
		self.board = Board(self.grid_size)
		# object의 외부 api는 state를 통해서만 이루어진다
		self.state = np.zeros(self.state_size, dtype=np.uint8)
		# 직전 진행 플레이어(1 or 2)
		self.playerJustMoved = 2
		# 승리 플레이어(default = 0)
		self.winner = 0

	#------------------------------------------------------------
	# 리셋
	#------------------------------------------------------------
	def reset(self):
		self.board = Board(self.grid_size)
		self.state = np.zeros(self.state_size, dtype=np.uint8)
		return self.state

	#------------------------------------------------------------
	# board 색을 뒤집음
	#------------------------------------------------------------
	def inverse(self):
		BLACK = 1
		WHITE = 2

		self.board.inverse()

		for i in range(self.state_size):
			if(self.state[i] == BLACK):
				self.state[i] = WHITE
			elif(self.state[i] == WHITE):
				self.state[i] = BLACK

	#------------------------------------------------------------
	# 현재 board 구함
	#------------------------------------------------------------
	def get_board(self):
		return self.board

	#------------------------------------------------------------
	# 현재 턴을 구함
	#------------------------------------------------------------
	def get_turn(self):
		return self.board.turn

	#------------------------------------------------------------
	# 클래스 복사
	#------------------------------------------------------------
	def Clone(self):
		temp = Env()
		temp.grid_size = self.grid_size
		temp.state_size = self.state_size
		temp.board = copy.deepcopy(self.board)
		temp.state = copy.deepcopy(self.state)
		temp.playerJustMoved = self.playerJustMoved
		return temp

	#------------------------------------------------------------
	# move를 실행해서 state를 업데이트
	#------------------------------------------------------------
	def DoMove(self, move):
		assert move >= 0 and move < self.state_size and move == int(move) and self.state[move] == 0
		self.playerJustMoved = 3 - self.playerJustMoved
		# board 업데이트
		x = int(move / self.grid_size)
		y = int(move % self.grid_size)
		self.board.put_value(self.playerJustMoved, x, y)
		# state 업데이트
		self.state[move] = self.playerJustMoved

	#------------------------------------------------------------
	# 현재 state에서 가능한 모든 move를 반환
	#------------------------------------------------------------
	def GetMoves(self):
		return [i for i in range(self.state_size) if self.state[i] == 0]

	#------------------------------------------------------------
	# playerJustMove의 관점에서 게임 결과 점수를 반환
	#------------------------------------------------------------
	def GetResult(self, playerjm):
		# 무승부
		if self.GetMoves() == [] and self.board.winner == 0:
			return 0.5
		# 승부 결정
		else:
			if self.board.winner == playerjm:
				return 1.0
			elif self.board.winner == (3 - playerjm):
				return 0.0
			else:
				return 0.5

	#------------------------------------------------------------
	# 출력용
	#------------------------------------------------------------
	def __repr__(self):
		s = ""
		for i in range(self.state_size):
			s += "_XO"[self.state[i]]
			if i % self.grid_size == 9:
				s += "\n"
		self.board.draw()
		return s

#------------------------------------------------------------
# MCTS Node
#------------------------------------------------------------
class Node:
	'''
		게임 트리의 노드
		승리는 항상 playerJustMoved의 관점에서 발생
		상태가 지정되지 않으면 충돌
	'''
	def __init__(self, move=None, parent=None, state=None):
		# 이 노드로 이동한 경우 - root 노드일 경우 "None"
		self.move = move
		# root 노드일 경우 "None"
		self.parentNode = parent
		self.childNodes = []
		self.wins = 0
		self.visits = 0
		# 미래의 child 노드
		self.untriedMoves = state.GetMoves()
		# 노드가 미래에 필요로 하는 state의 유일한 부분
		self.playerJustMoved = state.playerJustMoved

	def UCTSelectChild(self):
		'''
			UCB1 공식을 사용하여 하위 노드를 선택
			흔히 UCTK가 일정하게 적용되기 때문에 탐사와 착취의 양을 다양하게하기 위해 λc : c.wins / c.visits + UCTK * sqrt (2 * log (self.visits) /c.visits가 있음
		'''
		s = sorted(self.childNodes, key=lambda c: c.wins/c.visits +
		           math.sqrt(2*math.log(self.visits)/c.visits))[-1]
		return s

	def AddChild(self, m, s):
		'''
			untriedMoves에서 m을 제거하고이 이동에 대해 새 하위 노드를 추가
			추가 된 child 노드를 반환합니다.
		'''
		n = Node(move=m, parent=self, state=s)
		self.untriedMoves.remove(m)
		self.childNodes.append(n)
		return n

	def Update(self, result):
		'''
			이 노드를 업데이트
			한 번 더 방문하여 결과(wins)를 얻음
			결과는 playerJustmoved의 관점에서 발생해야함
		'''
		self.visits += 1
		self.wins += result

	def __repr__(self):
		return "[ Move:" + str(self.move) + ", Wins/Visits:" + str(self.wins) + "/" + str(self.visits)# + ", UntriedMoves:" + str(self.untriedMoves) + " ]"

	def TreeToString(self, indent):
		s = self.IndentString(indent) + str(self)
		for c in self.childNodes:
			 s += c.TreeToString(indent+1)
		return s

	def IndentString(self, indent):
		s = "\n"
		for i in range(1, indent+1):
			s += "| "
		return s

	def ChildrenToString(self):
		s = ""
		for c in self.childNodes:
			 s += str(c) + "\n"
		return s